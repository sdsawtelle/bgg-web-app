# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# -------------------------------------------------------------------------
# This is a sample controller
# - index is the default action of any application
# - user is required for authentication and authorization
# - download is for downloading files uploaded in the db (does streaming)
# -------------------------------------------------------------------------

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from time import sleep
import json
import sqlite3
import codecs
#
# class request:
#     pass
# request.folder = "C:/Users/Sonya/Box Sync/Projects/web-web2py-apps/applications/init"


def index():
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html

    if you need a simple wiki simply replace the two lines below with:
    return auth.wiki()
    """
    return dict(message=2)


def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    return dict(form=auth())




def geekbuddiesgraph():
    """Makes the d3.js force graph, with nodes color coded by similarity to the username received from form."""

    def format_link(source, target, value):
        """Return proper json formatting for links of force graph."""
        return {"source": source, "target": target, "value": value}

    def format_node(name, col, group):
        """Return proper json formatting for nodes of force graph."""
        return {"id": name, "group": group, "col": col}

    def compute_correlations(dbpath, nm, users):
        """Returns dataframe with usrs and their pearson correlation to name."""
        # Make a connection to the database housing ratings.
        connex = sqlite3.connect(dbpath)
        cur = connex.cursor()

        # Pull all the rows for where user is a user from the 2nd deg buddies list or the root user
        usrs = ["'" + usr + "'" for usr in users + [nm]]
        str_matching = "(" + ",".join(usrs) + ")"  # Construct the string of SQL language
        sql = "SELECT * FROM data WHERE username IN " + str_matching + ";"
        df = pd.read_sql_query(sql, connex)
        connex.close()

        # Was the user in our database? If not, get their ratings
        # r = req("http://www.boardgamegeek.com/xmlapi/collection/%s?rated=1" % (nm,))
        # soup = BeautifulSoup(r.text, "xml")  # Use the xml parser for API responses and the html_parser for scraping
        # gms = []
        # rats = []
        # for gm in soup("item"):
        #     gms.append(gm["objectid"])
        #     rats.append(int(gm.rating["value"]))

        # Pivot the dataframe up so that gameids become columns
        df = df.pivot_table(index="username", columns="gameid", values="ratings")

        # Center and normalize each row (user)
        df = df.sub(df.mean(axis=1), axis=0)  # Elementwise subtraction within each row
        rownorms = np.sqrt(np.square(df).sum(axis=1))  # A vector holding norms for each row
        df = df.divide(rownorms, axis=0)  # Elementwise division within each row
        df[df.isnull()] = 0  # put zero for missing ratings

        # Compute correlations and sort by them
        user = df.loc[nm, :].values
        df["correl"] = np.dot(df.as_matrix(), user.T)  # Compute pearson correlations
        df.drop(labels=nm, axis=0, inplace=True)  # Remove the row for the root user
        df.sort_values(by="correl", inplace=True, ascending=True)

        # Get stuff into the right format to create "node" json
        df["user"] = df.index
        return df

    def req(msg, slp=0.2):
        """Make fault tolerant BGG server requests."""
        # Sleep to make sure you are not pinging the server to frequently
        sleep(slp)
        # Keep trying requests until status-code is 200
        status_code = 500
        while status_code != 200:
            sleep(slp)
            try:
                r = requests.get(msg)
                status_code = r.status_code
                # if status_code != 200:
                    # print("Server Error! Response Code %i. Retrying..." % (r.status_code))
            except:
                # print("An exception has occurred, probably a momentory loss of connection. Waiting three seconds...")
                sleep(3)
        return r

    def random_user_sample(n=20):
        """Get random sample from the database."""
        userpath = os.path.join(request.folder, "databases", "bgg_users.csv")
        # with open(userpath, "rb") as myfile:
        #     users = pickle.load(myfile)

        users = pd.read_csv(userpath, header=None)
        users = users[0].sample(n=n).values
        users = list(set(users))
        return users


    # Get all first degree buddies for this user
    nm = request.vars["user_name"]
    r = req("http://www.boardgamegeek.com/xmlapi2/user?name=%s&buddies=1" % (nm,))
    soup = BeautifulSoup(r.text, "xml")  # Use the xml parser for API responses and the html_parser for scraping
    # buds = soup("buddy")
    first_deg_buds = [bud["name"] for bud in soup("buddy")]

    if len(first_deg_buds) > 20:
        first_deg_buds = list(np.random.choice(first_deg_buds, size=10))

    # Make the lists of 1st degree links and nodes
    first_deg_links = [format_link(nm, bud, 1) for bud in first_deg_buds]
    first_deg_nodes = [format_node(bud, 0, 1) for bud in first_deg_buds]

    # Get all the second degree stuff!
    second_deg_buds = []  # Unique second degree buddy names
    second_deg_links = []  # Links between second degree buds and their 1st deg bud "spawn point"
    second_deg_link_data = []
    second_deg_data = []  # Unique pairs of (2nd deg bud, grp) where grp identifies 1st deg bud who "owns" 2nd deg bud
    idx = 2  # Keeps track of "groups" - each group is all the 2nd deg buds spawned from the same first deg bud

    # For each 1st deg bud, get all his buddies
    for first_deg_bud in first_deg_buds:
        r = req("http://www.boardgamegeek.com/xmlapi2/user?name=%s&buddies=1" % (first_deg_bud,))
        soup = BeautifulSoup(r.text, "xml")  # Use the xml parser for API responses and the html_parser for scraping
        budlist = [bud["name"] for bud in soup("buddy")]

        # For each bud of a 1st degree bud, make a link b/w them that is very weak if that 2nd deg bud is already
        # present in the graph to this point. In this case a weak value will let the link distance stretch very long,
        # since the node for such a person will need to have multiple connections across the graph.
        for bud2 in budlist:
        #     if bud2 in first_deg_buds + second_deg_buds:
        #         second_deg_links += [format_link(first_deg_bud, bud2, 0.1)]
        #     else:
        #         second_deg_links += [format_link(first_deg_bud, bud2, 1)]
            second_deg_link_data += [(first_deg_bud, bud2)]

        # Add to list of unique 2nd deg buds and links (only if bud not already a 1st deg bud or the root user)
        second_deg_data += [(bud2, idx) for bud2 in budlist if bud2 not in second_deg_buds + first_deg_buds + [nm]]
        second_deg_buds += [bud2 for bud2 in budlist if bud2 not in second_deg_buds + first_deg_buds + [nm]]


        idx += 1  # Increment to identify the next "group" of 2nd deg buds

    # Compute correlations b/w root user and all the 2nd deg buds that are present in our DB
    dbpath = os.path.join(request.folder, "databases", "bgg_ratings.db")
    df = compute_correlations(dbpath, nm, second_deg_buds)


    # Restrict each 1st deg bud to spawning max of 30 2nd deg buds
    df_truncated = pd.DataFrame(columns=["correl", "user", "spawner"])
    spawner_dict = dict(zip(np.arange(2, len(first_deg_buds)+2), first_deg_buds))
    df["spawner"] = df["user"].map(dict(second_deg_data)).map(spawner_dict)
    for grpnm, grp in df.groupby("spawner"):
        sorted_grp = grp.sort_values(by="correl", ascending=False)
        df_truncated = pd.concat([df_truncated, sorted_grp.iloc[:20, :]])
    maxcorrel, mincorrel = df_truncated["correl"].max(), df_truncated["correl"].min()

    # Create all the second degree links
    # second_deg_link_data = [(first_deg_bud, bud2) for first_deg_bud, bud2 in second_deg_link_data]
    second_deg_link_data = [(first_deg_bud, bud2) for first_deg_bud, bud2 in second_deg_link_data if bud2 in df_truncated["user"]]
    second_deg_links = [format_link(first_deg_bud, bud2, 1) for first_deg_bud, bud2 in second_deg_link_data]
    # second_deg_links = [format_link(tup[0], tup[1], 1) for tup in df_truncated[["spawner", "user"]].itertuples()]

    # Make nodes for 2nd deg buds that were found in our DB
    tups = [(usr, corr) for idx, usr, corr in df_truncated[["user", "correl"]].itertuples()]
    second_deg_nodes = [format_node(tup[0], tup[1], 2) for tup in tups]

    # Add nodes for 2nd deg buds that were NOT in our DB (assign correlation zero)
    # second_deg_nodes += [format_node(bud, 0, 2) for bud in second_deg_buds if bud not in df["user"]]

    # Generate some random users and make nodes for those guys
    randusers = random_user_sample(n=400)
    randusers = [usr for usr in randusers if usr not in [nm] + first_deg_buds + second_deg_buds]
    df_rand = compute_correlations(dbpath, nm, randusers)

    # Get min and max correlation here if there were no second degree buds
    if np.isnan(maxcorrel):
        maxcorrel, mincorrel = df_rand["correl"].max(), df_rand["correl"].min()

    # Restrict best 50 and ceiling correlations to max correlation of 2nd deg buds
    df = df_rand.sort_values(by="correl", ascending=False).iloc[:15, :]
    df.loc[df["correl"] > maxcorrel, "correl"] = maxcorrel
    df.loc[df["correl"] < mincorrel, "correl"] = mincorrel
    tups = [(usr, corr) for idx, usr, corr in df[["user", "correl"]].itertuples()]
    random_nodes = [format_node(tup[0], tup[1], 3) for tup in tups]

    # Generate the full lists for nodes and for links
    nodes = [format_node(nm, 0, 0)] + first_deg_nodes + second_deg_nodes + random_nodes
    links = first_deg_links + second_deg_links

    # Write the full lists of nodes and links to json file
    jsonpath = os.path.join(request.folder, "static", "geekbuddies.json") # URL() helper didn't work here...
    # with open(jsonpath, 'w') as f:
    #     json.dump({"links": links, "nodes": nodes}, f, ensure_ascii=False)

    with codecs.open(jsonpath, 'w', encoding="utf-8") as f:
        json.dump({"links": links, "nodes": nodes}, f, ensure_ascii=False)

    return dict(maxcol=maxcorrel, mincol=mincorrel)




@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


