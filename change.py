import pickle, json

with open("checkidcookies.pkl","rb") as f:
    data = pickle.load(f)

with open("cookies.json","w") as f:
    json.dump(data,f)