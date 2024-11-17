# This file is for the data scraping and processing

'''Webscraping'''
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By               
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
import time 

'''Data Engineering'''
import pandas as pd
import numpy as np

'''Data Visualisation'''
import re

'''Sentiment Analysis'''
import praw
from dotenv import load_dotenv
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def get_ebay_data(user_input: str) -> pd.DataFrame:
    # Creating the webdriver
    driver = webdriver.Firefox()

    # The URL of eBay
    url = "https://www.ebay.de/?srsltid=AfmBOoqAmEZq1VwPS1t_FnwIgOr_vtGx-fzRKUCmQMCn-wQRzLjY6rLc"

    # Opening the webdriver
    driver.get(url)

    driver.implicitly_wait(10)
    time.sleep(3)

    # Accepting all cookies
    driver.find_element(By.ID, "gdpr-banner-accept").click()

    # Deleting all cookies
    driver.delete_all_cookies()

    time.sleep(3)
    # Finding the search box
    text_input = driver.find_element(By.ID, 'gh-ac') 

    # Clear the search box
    text_input.clear()  

    # Inserting the user input
    text_input.send_keys(user_input)    
    time.sleep(2)

    # Clicking enter
    text_input.send_keys(Keys.ENTER) 
    time.sleep(3)

    # Selecting the 'Sofort Kaufen'-Button
    time.sleep(3)
    driver.find_element(By.XPATH, '/html/body/div[5]/div[4]/div[1]/div/div[2]/div[2]/div[1]/div/ul/li[3]/a/span').click()
    time.sleep(3)

    # Finding the url of the first offers image
    product_image_url = driver.find_element(By.XPATH, "/html/body/div[5]/div[4]/div[3]/div[1]/div[3]/ul/li[2]/div/div[1]/div/a/div/img").get_attribute('src')
    product_image_url

    # Final data list
    data = []
    # Page counter
    page = 1
    # More pages boolean condition
    more_pages = True 

    # while-loop until pages under 31 and no more pages
    while page <= 30 and more_pages==True:
        # Setting up the soup with search result page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # all entries
        entries = soup.find_all('li', class_='s-item s-item__dsa-on-bottom s-item__pl-on-bottom')
        # next page button
        try:
            next_page_button = driver.find_element(By.CSS_SELECTOR, '.pagination__next')
        except:
            more_pages = False
        # page notification
        print(f'Now scraping page {page}')

        # Extracting information of each entrie on the page
        for entrie in entries:
            # Entrie dictionary
            entrie_data = {}
            # Adding the title
            entrie_data['title'] = entrie.find('div', class_='s-item__title').text
            # Adding the price
            entrie_data['price'] = entrie.find('span', class_='s-item__price').text[4:]
            # Adding the seller (Not always provided)
            try:
                entrie_data['seller'] = entrie.find('div', class_='s-item__subtitle').text
            except:
                entrie_data['seller'] = 'Not provided'
            # Append the data
            data.append(entrie_data)
        # Checking if there is a next page button
        try:
            page += 1
            next_page_button.click() 
            time.sleep(3)
        # Otherwise breaking condition
        except:
            more_pages=False

    # Converting into DataFrame
    data = pd.DataFrame(data)

    # 1. Remove the thousand separators (.) and replace the decimal separator (,) with a period (.)
    data['price'] = data['price'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)

    # Function to clean the price column
    def clean_price(price):
        # Handle ranges like "29.95 bis EUR 32.95" or "10 bis 20 EUR"
        if "bis" in price:
            prices = re.findall(r"\d+\.\d+", price)  # Extract all numeric values (float)
            if prices:
                return sum(map(float, prices)) / len(prices)  # Take the average of the range
        
        # Extract the first numeric value in the string (ignoring text like "EUR")
        cleaned_price = re.search(r"\d+\.\d+|\d+", price)
        return float(cleaned_price.group()) if cleaned_price else None  # Convert to float if a match is found

    # Apply the cleaning function to the 'price_clean' column
    data['price'] = data['price'].apply(clean_price)

    # Convert the cleaned price column to numeric
    data['price'] = pd.to_numeric(data['price'], errors='coerce')

    conditions = ["Neu", "Brandneu", "Neuwertig", "Sehr gut", "Gut", "Akzeptabel", "Neu mit Etikett", 
    "Neu ohne Etikett", "Neu mit Fehlern", "Neu: Sonstige (siehe Artikelbeschreibung)", 
    "Zertifiziert - Refurbished", "Neu mit Karton", "Neu ohne Karton", "Neu mit Fehlern",
    "Hervorragend - Refurbished", "Sehr gut - Refurbished", "Gut - Refurbished",
    "Vom Verkäufer generalüberholt", "Gebraucht", "Als Ersatzteil / defekt", "Repariert",
    "Gebraucht / Artikel wurde bereits benutzt", "Runderneuert", "Beschädigt", "Digitale Ware",
    "Bewertet", "Nicht bewertet"]

    seller_types = ["Privat", "Gewerblich"]

    # Create regular expressions for condition and seller type
    condition_pattern = '|'.join(map(re.escape, conditions))  # Escapes special characters if any
    seller_type_pattern = '|'.join(seller_types)  # Match Privat or Gewerblich

    # Extract condition and seller type from the seller column
    data['condition'] = data['seller'].str.extract(f'({condition_pattern})', expand=False)
    data['seller_type'] = data['seller'].str.extract(f'({seller_type_pattern})', expand=False)

    return data, product_image_url

def get_reddit_data(user_input: str) -> pd.DataFrame:
    # Load environment variables from .env file
    # Loading the .env file
    load_dotenv()

    # Accessing the credentials
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    user_agent = os.getenv('USER_AGENT')

    # Reddit API credentials
    reddit = praw.Reddit(client_id=f'{client_id}', 
                        client_secret=f'{client_secret}', 
                        user_agent=f'{user_agent}')

    # Search Reddit for posts related to the topic
    try:
        posts = []
        for post in reddit.subreddit('all').search(user_input, limit=500):
            posts.append([post.title, post.selftext])
    except Exception as e:
        print(f"An error occurred: {e}")

    # Convert scraped posts into a DataFrame
    posts_df = pd.DataFrame(posts, columns=['Title', 'Body'])

    # Initialize VADER sentiment analyzer
    analyzer = SentimentIntensityAnalyzer()

    # Example post from Reddit
    for post in posts:
        # Combining title and body for sentiment analysis
        text = post[0] + " " + post[1]
        sentiment_scores = analyzer.polarity_scores(text)
        
        # Display post title and sentiment analysis
        print(f"Post: {post[0]}")
        print(f"Sentiment Scores: {sentiment_scores}")
        print('---')

    # Function to get sentiment score for each post
    def get_sentiment(text):
        sentiment = analyzer.polarity_scores(text)
        return sentiment['compound']  # Compound score represents overall sentiment

    def get_overall_sentiment_score(posts_df):
        # Calculate sentiment for each post (combine title and body)
        posts_df['Sentiment'] = posts_df.apply(lambda row: get_sentiment(row['Title'] + ' ' + row['Body']), axis=1)

        # Calculate the overall average sentiment score
        overall_sentiment = posts_df['Sentiment'].mean()

        # Display the results
        return overall_sentiment

    
    def classify_sentiment(score):
        if score > 0.05:  # Threshold for positive sentiment
            return "Positive"
        elif score < -0.05:  # Threshold for negative sentiment
            return "Negative"
        else:
            return "Neutral"

    overall_classification = classify_sentiment(get_overall_sentiment_score(posts_df))

    posts_df['Sentiment_Classifier'] = posts_df['Sentiment'].apply(classify_sentiment)

    return posts_df, overall_classification