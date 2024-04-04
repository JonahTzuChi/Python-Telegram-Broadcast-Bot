# How to deploy?


# Create Sub-Folders Needed to Store Production Data
```
cd ./production
mkdir data error mongo
```

# Systerm Configuration
Duplicate `/deploy/example.env` as `/deploy/example.env` and fill up the blank.


# Bot Configuration
Under each `bot` folder, there is one folder named `config`. Two files can be found inside: `config.example.env` and `config.example.yml`. Duplicate and rename them like below.
```
cp config.example.env config.env
cp config.example.yml config.yml
```

Open both file individually and fill up the blank. Keep the original copy as a template and reference so that we can also refer back.