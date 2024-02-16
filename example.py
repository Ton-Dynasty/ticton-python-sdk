from ticton import TicTonAsyncClient
import asyncio

from dotenv import load_dotenv

load_dotenv()


async def tick(price):
    client = await TicTonAsyncClient.init(
        testnet=True,
    )
    await client.tick(price)


async def ring(alarm_id):
    client = await TicTonAsyncClient.init(
        testnet=True,
    )
    await client.ring(alarm_id)


async def wind(alarm_id, buy_num, price):
    client = await TicTonAsyncClient.init(
        testnet=True,
    )
    await client.wind(alarm_id, buy_num, price)


async def main():
    print("Please choose the function you want to execute: ")
    print("1. tick")
    print("2. ring")
    print("3. wind")
    choice = int(input("Enter your choice (1/2/3): "))

    if choice == 1:
        price = float(input("Enter the price: "))
        await tick(price)
    elif choice == 2:
        alarm_id = int(input("Enter the alarm id: "))
        await ring(alarm_id)
    elif choice == 3:
        alarm_id = int(input("Enter the alarm id: "))
        buy_num = int(input("Enter the buy num: "))
        price = float(input("Enter the price: "))
        await wind(alarm_id, buy_num, price)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
