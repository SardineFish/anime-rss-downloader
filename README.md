# Anime RSS Downloader

Fetch anime torrent url from RSS and send to transmission download.

Tested:
- dmhy
- mikan

Thanks GPT 4o mini help developing this.

## Requirement

- Python 3.?
- [Transmission](https://transmissionbt.com/) service with RPC

## Setup

Create an virtual environment at `.venv`

```shel
$ python -m venv ./.venv
```

Activate virtual environment and install requirements

```shell
$ ./setup.sh
```

## Configuration

Create a `config.yaml`

See `config-example.yaml` for configuration details.

```shell
$ cp config-example.yaml config.yaml
```

## Run

```shell
$ ./run.sh
```

## Auto Run

Use crontab to fetch downloads daily

```shell
$ crontab -e
```

Add following task to crontab

```crontab
# Run at 04:05:00 daily
5 4 * * * /path/to/anime-download/run.sh
```

## Loging

Logging save to `./download.log` by default.

## Docker
TODO