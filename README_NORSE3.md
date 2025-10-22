# AIDR-Bastion Norse3 Fork

AIDR-Bastion 

## Setup

Requirements;
    - Python3.12, python3.12-dev, python3.12-venv
    - 10GB space (pytorch)


```bash
make setup PIP_CACHE_DIR=/path/to/your/cache/tmp
```

## Running

```bash
make start
```

## Deployments

Build a docker image (8.3GB!);
```bash
make build-image
```


## License

Under obligations to the LGPL license attached to AIDR-Basion, the original source code can be found here; https://github.com/0xAIDR/AIDR-Bastion

#### References

- (LGPL in a SaaS product) https://chatgpt.com/share/68f8a6ee-2534-8002-a293-03e610d82c6d
- (setup: problem with nltk zip package) https://github.com/0xAIDR/AIDR-Bastion/issues/25