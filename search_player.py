import json
import os
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GraphQL endpoint
url = "https://api.sorare.com/federation/graphql"

transport = AIOHTTPTransport(
    url=url,
    headers={"APIKEY": os.getenv("SORARE_API_KEY")},
)
client = Client(transport=transport, fetch_schema_from_transport=True)

# Function to execute a GraphQL query
async def execute_query(query):
    async with Client(
        transport=transport, fetch_schema_from_transport=True
    ) as session:
        result = await session.execute(query)
    return result

# Function to fetch all pages of results
async def fetch_all_players():
    players = []
    has_next_page = True
    cursor = ""

    while has_next_page:
        query_template = f"""
        {{
            football {{
                allCards(first: 100, after: "{cursor}") {{
                    nodes {{
                        player {{
                            slug
                            displayName
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
        query = gql(query_template)
        result = await execute_query(query)
        cards = result["football"]["allCards"]["nodes"]
        print(cards)
        page_info = result["football"]["allCards"]["pageInfo"]

        players.extend(cards)
        cursor = page_info["endCursor"]
        has_next_page = page_info["hasNextPage"]

    return players

# Main function to encapsulate the logic
async def main():
    players = await fetch_all_players()
    player_data = [{"slug": player["player"]["slug"], "displayName": player["player"]["displayName"]} for player in players if "player" in player]
    
    with open("all_players.json", "w") as file:
        json.dump(player_data, file, indent=4)

    print("Player data has been saved to players.json")

# Execute the main function
asyncio.run(main())
