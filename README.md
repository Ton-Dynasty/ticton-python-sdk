# TicTon Python SDK

This is the Python SDK for Tic Ton Oracle on TON blockchain, which is a pure decentralized oracle protocol that can provide latest price with high precision guraranteed by incentive mechanism.

## Installation
Install the SDK using pip:
```bash
pip install ticton
```

## (Optional) Setting the Environment Variables
The SDK requires several environment variables for its operation.You can set the environment variables using the `export` command in your shell. Here are the variables you need to set:
- `TICTON_WALLET_MNEMONICS`: A space-separated list of mnemonics used for wallet authentication and operations.
- `TICTON_WALLET_VERSION`: Specifies the wallet version. Supported values are "v2r1", "v2r2", "v3r1", "v3r2", "v4r1", "v4r2", "hv2". The default is "v4r2".
- `TICTON_ORACLE_ADDRESS`: The address of the oracle smart contract on the TON blockchain.
- `TICTON_TONCENTER_API_KEY`: An API key for accessing TON blockchain data. You can apply for an API key at [@tonapibot](https://t.me/tonapibot).
- `TICTON_THRESHOLD_PRICE`: A float value that sets a threshold price, with a default of 0.7.
```bash
export TICTON_WALLET_MNEMONICS="word1 word2 word3 ... wordN"
export TICTON_WALLET_VERSION="v4r2"
export TICTON_ORACLE_ADDRESS="your_oracle_address"
export TICTON_TONCENTER_API_KEY="your_api_key"
export TICTON_THRESHOLD_PRICE=0.7
```
## Initialization
If you have already set the environment variables by using the `export` command, you can easily initialize the ticton client using the following code:
```python
from ticton import TicTonAsyncClient

client = await TicTonAsyncClient.init()
```
Alternatively, if you prefer not to set global environment variables, you can pass these directly to the initialization function:
```python
from ticton import TicTonAsyncClient

client = await TicTonAsyncClient.init(
    wallet_mnemonics="word1 word2 word3 ... wordN",
    wallet_version="v4r2",
    oracle_address="your_oracle_address",
    toncenter_api_key="your_api_key",
    threshold_price=0.7
)
```

## Usage Example
[Use Case - Ticton Oracle Automation](https://github.com/Ton-Dynasty/ticton-oracle-automation/tree/main)

### Tick
tick will open a alarm with the given price and timeout, the total amount
of baseAsset and quoteAsset will be calculated automatically.

#### Parameters
- `price` : float
  - The price of the alarm quoteAsset/baseAsset
- `timeout` : int (optional, default=1000)
  - The timeout of the alarm in seconds
- `extra_ton` : float (optional, default=0.1)
  - The extra ton to be sent to the oracle
#### Example

Assume the token pair is TON/USDT, the price is 2.5 USDT per TON
```python
price = 2.5

result = await client.tick(price)
```
### Ring
ring will close the alarm with the given alarm_id

#### Parameters
- `alarm_id` : int
  - The alarm_id of the alarm to be closed
#### Example
```python
alarm_id = 1

result = await client.ring(alarm_id)
```
### Wind
wind will arbitrage the alarm with the given alarm_id, buy_num and new_price

#### Parameters
- `alarm_id` : int
  - The alarm_id of the alarm to be arbitrage
- `buy_num` : int
  - The number of tokens to be bought, at least 1.
- `new_price` : float
  - The new price of the alarm quoteAsset/baseAsset

#### Example
Assume the token pair is TON/USDT, the price is 2.5 USDT per TON. The alarm is opened with 1 TON and 2.5 USDT with index 123.
The new price is 5 USDT per TON, the buy_num is 1.
```python
alarm_id = 123
buy_num = 1
new_price = 5

result = await client.wind(alarm_id, buy_num, new_price)
```
### Subscribe
subscribe will subscribe the oracle's transactions, handle the transactions and call the
given callbacks.

#### Parameters
- `on_tick_success`: function
  - The callback function to be called when the tick transaction is successful, with the following parameters:
    - `watchmaker` : str
    - `base_asset_price` : float
    - `new_alarm_id` : int
    - `created_at` : int

- `on_ring_success`: function
  - The callback function to be called when the ring transaction is successful, with the following parameters:
    - `alarm_id` : int
    - `created_at` : int
    - `origin` : str
    - `receiver` : str
    - `amount` : int 

- `on_wind_success`: function
  - The callback function to be called when the wind transaction is successful, with the following parameters:
    - `timekeeper` : str
    - `alarm_id` : int
    - `new_base_asset_price` : float
    - `remain_scale` : int
    - `new_alarm_id` : int
    - `created_at` : int

- start_lt: int, "oldest", "latest" (optional, default="oldest")
  - From when to yield transaction, default to replay the transaction from the oldest transaction

#### Examples
```python
async def on_tick_success(params: OnTickSuccessParams):
    print(f"Tick success", params.model_dump())

async def on_ring_success(params: OnRingSuccessParams):
    print(f"Tick success", params.model_dump())

async def on_wind_success(params: OnWindSuccessParams):
    print(f"Tick success", params.model_dump())

await client.subscribe(on_tick_success, on_ring_success, on_wind_success)
```


## Development Guide

### Install

1. Make sure [poetry](https://python-poetry.org/docs/#installation) installed on your machine.

    > you may need to set the `PATH` environment variable to include the Poetry binary directory, e.g. `export PATH="$HOME/.local/bin:$PATH"`

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2. Install plugin for poetry

    ``` bash
    poetry self add poetry-bumpversion
    poetry self add poetry-plugin-export
    ```

3. Install dependencies

    ```bash
    make install
    ```

4. Start your virtual environment

    ```bash
    poetry shell
    ```

5. Run tests

    ```bash
    poetry run pytest
    ```
