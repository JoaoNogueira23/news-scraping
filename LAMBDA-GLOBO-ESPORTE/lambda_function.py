from bs4 import BeautifulSoup
import requests
import string
import os
import mysql.connector
from datetime import datetime, timedelta
import boto3


### VARIABLES ###
args_database = {
    'mysql_host': os.environ['mysql_host'],
    'mysql_credential': os.environ['mysql_username'],
    'mysql_database': os.environ['mysql_database'],
    'mysql_password': os.environ['mysql_password']
}

ingestion_date = (datetime.today() - timedelta(hours=3)).strftime('%Y-%m-%d %H-%M-%S')

### headers for requests in web sites
headers = {'accept': '*/*',
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.53','Accept-Language': 'en-US,en;q=0.9,it;q=0.8,es;q=0.7'
}

####  FUNCTIONS ####
def extract_headline(soup, keywords, site_name, id_site):
    values_insert = []

    headline_date = soup.find(class_ = 'bs-home').get('data-generated-at')

    content = soup.find_all(class_ = 'feed-post')

    for item in content:
        ### info extract from html ###
        title = item.find(class_ = 'feed-post-body-title')

        title_text = title.find('p').get_text().strip()

        url_news = title.find('a')['href']

        describe = item.find(class_ = 'feed-post-body-resumo').get_text().strip()

        # mapping for found keywors in title
        translator = str.maketrans('', '', string.punctuation)

        clean_sentence = title_text.translate(translator)

        words_in_title = set(clean_sentence.lower().split())

        found_keywords = keywords.intersection(words_in_title)


        if found_keywords:
            values_insert.append((title_text, describe, headline_date, ingestion_date, site_name, url_news, id_site))

        
    return values_insert

    
def mysql_connection(args_database):
    try:
        # Configurações de conexão
        config = {
            'user': args_database['mysql_credential'],
            'password': args_database['mysql_password'],
            'host': args_database['mysql_host'],
            'database': args_database['mysql_database']
        }

        conn = mysql.connector.connect(**config)

        return conn
    except Exception as err:
        print("Database connection failed!")

def insert_into_tb(conn, cursor, results):

    # Comando SQL para inserção de dados
    query_insert = """
    INSERT INTO TB_SCRAPING_FT.TB_NEWS
    (hideline, resume, `date`, ingestionDate, site_name, id_site, url_news)
    VALUES(%s, %s, %s, %s, %s, %s, %s);"""

    # Executando o comando
    cursor.executemany(query_insert, results)

    # Confirmando a inserção
    conn.commit()

    print(cursor.rowcount, "registro(s) inserido(s).")


def lambda_handler(event, content):

    conn = mysql_connection(mysql_password=args_database['mysql_password'])

    cursor = conn.cursor()

    try:
        site = event['site']
        url = site['url']
        site_name = site['site_name']
        id_site = int(site['id_site'])
        keywords = event['keywords']

        response = requests.get(url, headers=headers)

        soup = BeautifulSoup(response.text)
        
        results = extract_headline(soup, keywords, site_name, id_site)

        insert_into_tb(conn, cursor, results)

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'content': results
        }
        
    
    except Exception as err:
        print(err)
        return {
            'statuCode': 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'message': "Error during scraping"
        }

    finally:
        cursor.close()
        conn.close()
