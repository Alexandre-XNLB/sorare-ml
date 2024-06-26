import json
import os
from datetime import datetime
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import csv
from dotenv import load_dotenv

load_dotenv()

league = "premier-league"
with open("data/" + league + ".json", "r") as file:
    league_data = json.load(file)

# GraphQL endpoint
url = "https://api.sorare.com/federation/graphql"

# Directory to save the data
data_dir = "data/" + league
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
os.makedirs(data_dir + "/clubs", exist_ok=True)


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

        return all_scores

async def fetch_club_players(slug):
    async with Client(transport=transport) as session:
        query_template = """
        {{
            football {{
                club(slug: "{slug}") {{
                    activePlayers {{
                        nodes {{
                            slug
                            displayName
                            position
                            so5Scores(last:15) {{
                                score
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """

        query = query_template.format(slug=slug)
        data = await session.execute(gql(query))
        return data

def format_datetime(date_str):
    # Parse the datetime string to a datetime object
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    # Format the datetime object to the desired string format
    return dt.strftime("%Y-%m-%d %H:%M:%S")

async def main():
    for club in league_data["data"]["football"]["competition"]["clubs"]["nodes"]:
        club_slug = club["slug"]
        club_data = await fetch_club_players(club_slug)

        if club_data:
            print(f"Saving data for {club_slug}")
            with open(f"{data_dir}/clubs/{club_slug}.json", "w") as jsonfile:
                json.dump(club_data, jsonfile, indent=4)
        
        
        for player in club_data["football"]["club"]["activePlayers"][
            "nodes"
        ]:
            slug = player["slug"]
            score_data = await fetch_player_scores(slug)

            if score_data:
                print(f"Saving data for {slug}")
                score_data.reverse()  # Reverse the list to start with the oldest entry
                with open(f"{data_dir}/{slug}.csv", "w", newline="") as csvfile:
                    fieldnames = ["datetime", "score"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    for item in score_data:
                        formatted_date = format_datetime(item["game"]["date"])
                        writer.writerow(
                            {"datetime": formatted_date, "score": item["score"]}
                        )

        print("Data fetching and saving completed.")

import asyncio
asyncio.run(main())