
# Here will be the code for the frontend

from enum import Enum, auto

import pandas as pd
import streamlit as st
from streamlit import session_state as ss
import plotly.express as px
import data
import plotly.graph_objects as go
import numpy as np

# --- Streamlit Configuration ---
st.set_page_config(page_title="Market Screener", page_icon="🛒", layout="wide")

def reset_app():
    """Resets the app."""

    # clear session state
    ss.clear()
    initialize_session_state()

    # clear cache
    st.cache_data.clear()
    st.cache_resource.clear()


# --- App Stages ---
class AppStage(Enum):
    """Enum for the different stages of the app."""

    START = auto()
    ANALYSIS_START = auto()

    # define greater or equal
    def __ge__(self, other):
        return self.value >= other.value


# --- Session State Initialization ---
def initialize_session_state():
    """Initializes the session state."""
    if "app_stage" not in ss:
        ss["app_stage"] = AppStage.START
    if "df" not in ss:
        ss["df"] = pd.DataFrame()
    if "analysis_started" not in ss:
        ss["analysis_started"] = False
    if "analysis_done" not in ss:
        ss["analysis_done"] = False
    if "show_visuals" not in ss:
        ss["show_visuals"] = False  # Default to False (using full dataset)


initialize_session_state()


# --- Helper Functions ---
def increment_edit_table_id():
    """Increments the edit table ID."""
    ss["edit_table_id"] = ss["edit_table_id"] + 1


def show_price_plots(data):
    # 1. Histogram of Prices
    st.subheader("Price Distribution")
    fig1 = px.histogram(data, x='price', color='condition', nbins=10, title='Price Distribution',
                        labels={'price': 'Price (in EUR)'}, marginal='violin', opacity=0.7)
    fig1.update_layout(bargap=0.1, template='plotly_white')
    st.plotly_chart(fig1)

    # 2. Boxplot of Prices by Condition
    st.subheader("Price by Condition")
    fig2 = px.box(data, x='condition', y='price', color='condition', title='Price by Condition',
                  labels={'condition': 'Condition', 'price': 'Price (in EUR)'})
    fig2.update_layout(template='plotly_white', xaxis=dict(title="Condition", tickangle=45))
    st.plotly_chart(fig2)

    # 3. Bar Plot: Count of Products by Condition
    st.subheader("Count of Products by Condition")
    fig3 = px.bar(data, x='condition', title='Count of Products by Condition',
                  labels={'condition': 'Condition'}, color='condition')
    fig3.update_layout(template='plotly_white', xaxis=dict(title="Condition", tickangle=45))
    st.plotly_chart(fig3)

    # 4. Pie Chart: Seller Status Distribution
    st.subheader("Seller Status Distribution")
    seller_status_counts = data['seller_type'].value_counts()
    fig4 = go.Figure(data=[go.Pie(labels=seller_status_counts.index, values=seller_status_counts,
                                  textinfo='label+percent', insidetextorientation='radial')])
    fig4.update_traces(marker=dict(colors=['#66b3ff', '#99ff99', '#ffcc99'], line=dict(color='#000000', width=2)))
    st.plotly_chart(fig4)

def get_histogram_plotly(sentiment_data):
    # Define the bin edges and histogram data
    bins = np.linspace(min(sentiment_data), max(sentiment_data), 20)
    hist, bin_edges = np.histogram(sentiment_data, bins=bins)

    # Set up colors based on sentiment ranges
    colors = ['red' if x < -0.2 else 'grey' if -0.2 <= x <= 0.2 else 'green' for x in bin_edges[:-1]]

    # Create the histogram using Plotly
    fig = go.Figure()

    # Add bars to the figure
    for i in range(len(hist)):
        fig.add_trace(go.Bar(
            x=[(bin_edges[i] + bin_edges[i + 1]) / 2],  # Bin center for each bar
            y=[hist[i]],
            width=[bin_edges[i + 1] - bin_edges[i]],  # Bin width
            marker_color=colors[i],
            name=f"Bin {i + 1}"
        ))

    # Add vertical line at sentiment score 0 (neutral)
    fig.add_shape(
        type="line",
        x0=0, x1=0,
        y0=0, y1=max(hist),
        line=dict(color="black", dash="dash"),
        name="Neutral Score"
    )

    # Update the layout
    fig.update_layout(
        title="Distribution of Sentiment Scores",
        xaxis=dict(title="Sentiment Score"),
        yaxis=dict(title="Number of Posts"),
        showlegend=False,  # Disable individual bar legends
        template="plotly_white"
    )

    # Add custom legend
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="markers",
        marker=dict(color="red", size=10),
        name="Negative"
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="markers",
        marker=dict(color="grey", size=10),
        name="Neutral"
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="markers",
        marker=dict(color="green", size=10),
        name="Positive"
    ))

    return fig

def get_donut_chart_plotly(sentiment_data):
    # Prepare data for the donut chart
    rating_counts = sentiment_data['Sentiment_Classifier'].value_counts().sort_index()
    labels = rating_counts.index
    sizes = rating_counts.values

    # Define custom colors for each sentiment class
    custom_colors = {
        'Negative': '#FF1111',
        'Neutral': '#808080',
        'Positive': '#397D22'
    }
    colors = [custom_colors[label] for label in labels]

    # Create the donut chart
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=sizes, 
        hole=0.6,  # Set the hole size for a donut chart
        marker=dict(colors=colors),
        textinfo='label+percent',  # Show labels and percentage
        hoverinfo='label+value+percent'  # Show detailed hover information
    )])

    # Update layout
    fig.update_layout(
        title="Distribution of Sentiment Classes",
        annotations=[dict(text="Sentiment", x=0.5, y=0.5, font_size=20, showarrow=False)],
        showlegend=True
    )

    return fig


# --- Main App Logic ---
st.title("Market Screener 🛒 x 🤖")
st.write(
    "Welcome to the Market Screener, where you can find a sufficient and overall analysis for any product you are looking for!\nNotice: The quality of the result correlates highly with your input specification. So be as accurate as you can be!"
)
st.write(
    "This model is still in beta - We are happy to hear your feedback. Please report any issues to Claas Resow."
)

selected_option = st.text_input(
        "Search for product you want to analyze::", placeholder="E.g. MacBook Air 2020 1TB"
    )

st.write("Data scraping starts...")

tab1, tab2, tab3 = st.tabs(["Plots", "KPIs", "Data Preview"])

ebay_df, product_image_url = data.get_ebay_data(selected_option)
reddit_df, overall_sentiment_score = data.get_reddit_data(selected_option) 
st.image(product_image_url, caption=f"{selected_option} Picture")

with tab1:
    
    st.plotly_chart(show_price_plots(data.get_ebay_data(selected_option)))
    st.plotly_chart(get_histogram_plotly(data.get_reddit_data(selected_option)))
    st.plotly_chart(get_donut_chart_plotly(data.get_reddit_data(selected_option)))
    

with tab2:
    st.write("### KPIs")
    st.write(f"Mean Price: {ebay_df.price.mean()}")
    st.write(f"Median Price: {ebay_df.price.median()}")
    st.write(f"Overall Sentiment Score: {overall_sentiment_score}")


    grouped = data.groupby(['condition', 'seller_type'])['price'].mean().reset_index()
    # Pivot the table to compare the prices side by side
    pivoted = grouped.pivot(index='condition', columns='seller_type', values='price')
    # Calculate the average price difference between seller types for each condition
    pivoted['price_difference_percent'] = ((pivoted['Gewerblich'] - pivoted['Privat'])/pivoted['Privat'])*100
    # Mean Difference of the seller type prices in all conditions
    avg_price_by_seller_type_and_condition = pivoted['price_difference_percent'].mean()
    # Conditional print
    if avg_price_by_seller_type_and_condition > 0:
        st.write(f"The prices from Privat for each condition are on average {avg_price_by_seller_type_and_condition:.2f}% cheaper than from Gewerblich.")
    else:
        st.write(f"The prices from Gewerblich for each condition are on average {(avg_price_by_seller_type_and_condition * -1):.2f}% cheaper than from Privat.")
    
    

with tab3:
    # Show data preview
    df = data.get_ebay_data(selected_option)
    st.write("### Data Preview")
    st.dataframe(df.head())




st.button("Reset App", on_click=reset_app)
