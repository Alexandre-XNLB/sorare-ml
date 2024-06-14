import json
import os
from datetime import datetime, timedelta
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import csv
import asyncio
import os
from dotenv import load_dotenv
import pandas as pd

userslug = "bananederungis"

# GraphQL endpoint
url = "https://api.sorare.com/federation/graphql"

# Directory to save the data
data_dir = "data/" + userslug
if not os.path.exists(data_dir):
    os.makedirs(data_dir)


load_dotenv()

transport = AIOHTTPTransport(
    url="https://api.sorare.com/federation/graphql",
    headers={
       'APIKEY': os.getenv('SORARE_API_KEY')
    },
)

async def fetch_player_scores(slug):
    all_scores = []
    async with Client(transport=transport) as session:
        query_template = """
            {{
            football {{
                player(slug: "{slug}") {{
                    allSo5Scores(after: "{after}", first: 50) {{
                        pageInfo {{
                        hasNextPage
                        endCursor
                        }}
                        nodes {{
                        score
                        game {{
                            date
                        }}
                        }}
                    }}
                }}
            }}
            }}
            """
        after_cursor = ""  # Start with no cursor
        has_next_page = True

        while has_next_page:
            query = query_template.format(slug=slug, after=after_cursor)
            data = await session.execute(gql(query))
            scores_data = data["football"]["player"]["allSo5Scores"]
            nodes = scores_data["nodes"]
            all_scores.extend(nodes)

            has_next_page = scores_data["pageInfo"]["hasNextPage"]
            if has_next_page:
                after_cursor = scores_data["pageInfo"]["endCursor"]

        # Sort scores by game date from oldest to newest
        all_scores.sort(key=lambda x: x["game"]["date"])
        return all_scores

async def fetch_my_players(userslug, transport, limit=50):
    async with Client(transport=transport) as session:
        all_players = []
        has_next_page = True
        end_cursor = None
        
        while has_next_page:
            query_template = """
            {{
                user(slug: "{user_slug}") {{
                    footballCards(first: {limit}, after: "{after_cursor}") {{
                        nodes {{
                            player {{
                                slug
                                displayName
                                position
                                so5Scores(last:15) {{
                                    score
                                }}
                            }}
                        }}
                        pageInfo {{
                            endCursor
                            hasNextPage
                        }}
                    }}
                }}
            }}
            """

            query = query_template.format(user_slug=userslug, limit=limit, after_cursor=end_cursor or "")
            data = await session.execute(gql(query))

            # Append the current page of players to all_players
            football_cards = data['user']['footballCards']
            all_players.extend(football_cards['nodes'])

            # Update pagination variables
            page_info = football_cards['pageInfo']
            has_next_page = page_info['hasNextPage']
            end_cursor = page_info['endCursor']

        return all_players

def format_datetime(date_str):
    # Parse the datetime string to a datetime object
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    # Format the datetime object to the desired string format
    return dt.strftime("%Y-%m-%d %H:%M:%S")

async def main():
    club_data = await fetch_my_players(userslug, transport)
    
    end_date = pd.to_datetime("2024-02-19")

    with open(f"predictions.csv", "w", newline="") as prediction_csvfile:
        fieldnames = ["datetime", "score", "player_slug"]
        prediction_writer = csv.DictWriter(prediction_csvfile, fieldnames=fieldnames)
        prediction_writer.writeheader()
        
        for player in club_data:
            slug = player["player"]["slug"]
            score_data = await fetch_player_scores(slug)
            
            if score_data:
                print(f"Saving data for {slug}")
                score_data = [item for item in score_data if item["score"] > 0]

                number_of_rows = len(score_data)
                if number_of_rows < 40:
                    continue
                
                start_date = end_date - pd.Timedelta(days=number_of_rows - 1)
                date_range = pd.date_range(start_date, periods=number_of_rows, freq="D")

                # Save individual player data
                with open(f"{data_dir}/{slug}.csv", "w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for date, item in zip(date_range, score_data):
                        writer.writerow(
                            {"datetime": date.strftime("%Y-%m-%d %H:%M:%S"), "score": item["score"], "player_slug": slug}
                        )

                # Get last 5 game scores
                last_5_games_dates = date_range[-5:]
                for date, game in zip(last_5_games_dates, score_data[-5:]):
                    prediction_writer.writerow({"datetime": date.strftime("%Y-%m-%d %H:%M:%S"), "score": game["score"], "player_slug": slug})
                
                # Add 2 null rows for the next 2 days
                last_game_date = last_5_games_dates[-1]
                for i in range(1, 3):
                    future_date = last_game_date + pd.Timedelta(days=i)
                    prediction_writer.writerow({"datetime": future_date.strftime("%Y-%m-%d %H:%M:%S"), "score": None, "player_slug": slug})

    print("Data fetching and saving completed.")
    
asyncio.run(main())