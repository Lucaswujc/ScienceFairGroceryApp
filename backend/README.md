2025-12-27

Decision : both sqlite engine and the file system based engine are implemented, the sqlite engine is implemented in db_engine/sqlite_engine.py
the file system engine is implemented under crawlwer/utils.py 

create a folder test_data to store the data can be used for tests. 
a sample cralwer_results.db is copied here,
also fiel system based data can be placed under here. 


2025-09-10
- [x] 1. Linked changed to kroger.com/weeklyad/weeklyad instead of kroger.com/weeklyad, and able to create production description with price and image
1a. Website is blocking us sometimes, need to find a way around it (idea: retry multiple times when error detected)

- [x] 2. Find a way to store information persistently and retrieve if requested by frontend
- [x] 3. Parse tomthumb, heb
4. Build server api so it can respond to frontend requests

- [x] store data in backend
idea 1: design a folder structure scheme, every parse results in data stored in folder
design a text-file format  - json easiest way, persisted on disc

- [x] idea 2: specialized db to store json file, key-value - 
mangodb - easiest way to create is docker, python program to talk to mangodb
structure key value
how to store image in json - hex value string

Went with json file format - simpler to implement than mongo db - our data is not that big
sort of dictionary that can account for the different atrtibutes we parsed from each website
