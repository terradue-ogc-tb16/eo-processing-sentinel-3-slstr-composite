## SNAP and Sentinel-3

### Using Binder

Click the badge below to run this notebook on Binder:

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/terradue-ogc-tb16/eo-processing-sentinel-3-slstr-composite/master?urlpath=lab)

### Run locally using docker

#### Use the built docker image

TBW

#### Build the image
Clone this repository with:

```bash
git clone https://gitlab.com/terradue-ogctb16/eoap/d169-jupyter-nb/eo-processing-sentinel-3-slstr-composite.git
```

Go to the directory containing the cloned repository:

```bash
cd eo-processing-sentinel-3-slstr-composite
```

Use docker compose to build the docker image:

```bash
docker-compose build
```

This step can take a few minutes...

Finally run the docker with:

```
docker-compose up
```

Open a browser window at the address http://0.0.0.0:9005 and run the notebook
