# bgg-web-app
The boardgamegeek friend finder and social graph visualization web2py app.

This is a simple app built with the web2py framework and hosted on pythonanywhere.com. The app accepts a username from the boardgamegeek.com (BGG) community, and produces a d3.js visualization of that users GeekBuddy social graph. The visualization is tailored to the purpose of helping users discover more GeekBuddies -in particular, second-degree connections (potential friends to add) are color coded according to a similarity metric based on ratings of boardgames in the BGG database. Data for the similarity computation was acquired via scraping and API calls to the BGG server. Note that the data lives in a sqlite database that is too large to be moved to the pythonanywhere servers in one piece (for us lowly "free tier" users). Therefore, there is a script that chunks my database on my PC and uploads the chunks to a seperate github repo. On the pythonanywhere servers I then pull the chunks down and reconstruct them with a script. The database repo is [here](https://github.com/sdsawtelle/bgg-web-app).

A more detailed write up about the data acquisition, the similarity metric algorithm and the setup and workflow (web2py + pythonanywhere) can be had at:
- [data acquisition with scraping and API calls]()
- [similarity metric algorithm from boardgame ratings]()
- [web2py and pythonanywhere setup and workflow]()

###Known Bugs:
- Fails when user is not in database (in compute_correlations, tries to drop row with "user" but row doesn't exist)
- Doesn't account for people that have you in their buddy list

###To-Do List:
- **Redesign! Make it "build out" as far as needed to provide 200 (?) high quality nodes.**
- Make landing page more visually appealing
- Clean up controller code
- Explore better similarity metrics
- Colorbar for similarity metric
