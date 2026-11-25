"""Month-by-month 'When to go' guide shown on the home page.

Scores: 3 = excellent, 2 = good, 1 = possible (rainy / quieter season).
"""

SEASONS = [
    {"m": "Jan", "name": "January", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "Calving season in the Serengeti",
     "text": "Thousands of wildebeest calves are born on the short-grass plains of Ndutu and the southern Serengeti, "
             "drawing lions and cheetahs. Warm, mostly dry days make it a great month for Kilimanjaro too."},
    {"m": "Feb", "name": "February", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "Peak calving and predator action",
     "text": "The best month to see newborn wildebeest and big cats on the hunt. Clear skies on the mountain and "
             "hot, sunny beach days in Zanzibar."},
    {"m": "Mar", "name": "March", "safari": 2, "kili": 2, "zanzibar": 2,
     "title": "Green season begins",
     "text": "The landscape turns green and the parks are quiet. Short showers start late in the month, "
             "with lower prices and fewer vehicles at sightings."},
    {"m": "Apr", "name": "April", "safari": 1, "kili": 1, "zanzibar": 1,
     "title": "Long rains, lowest prices",
     "text": "The wettest month. Safaris still run and the parks are lush and empty. On Kilimanjaro "
             "we recommend the drier northern Rongai route."},
    {"m": "May", "name": "May", "safari": 1, "kili": 1, "zanzibar": 1,
     "title": "Quiet, green and great value",
     "text": "Rains ease towards the end of the month. The herds start moving north through the central "
             "Serengeti; a good time for travellers who want the parks almost to themselves."},
    {"m": "Jun", "name": "June", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "Dry season and the western corridor",
     "text": "Cool, dry weather returns. The migration gathers in the western corridor around the Grumeti River, "
             "and the Kilimanjaro high season begins."},
    {"m": "Jul", "name": "July", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "Mara River crossings start",
     "text": "The famous river crossings begin in the northern Serengeti. Excellent game viewing everywhere as "
             "animals gather around water. Book early: this is peak season."},
    {"m": "Aug", "name": "August", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "The best of everything",
     "text": "Dramatic crossings in the north, superb wildlife in Tarangire and the Ngorongoro Crater, clear summit "
             "nights on Kilimanjaro and perfect beach weather."},
    {"m": "Sep", "name": "September", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "Crossings and clear skies",
     "text": "Herds still crossing the Mara River. Dry, sunny days make it one of the most reliable months "
             "for both a safari and a climb."},
    {"m": "Oct", "name": "October", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "Dry season highlights",
     "text": "Big herds in the northern Serengeti and fantastic elephant viewing in Tarangire. Fewer visitors "
             "than in August, with excellent climbing conditions."},
    {"m": "Nov", "name": "November", "safari": 2, "kili": 2, "zanzibar": 2,
     "title": "Short rains, herds head south",
     "text": "Brief afternoon showers freshen the plains and the migration moves back south. "
             "A quieter time with good-value prices."},
    {"m": "Dec", "name": "December", "safari": 3, "kili": 3, "zanzibar": 3,
     "title": "Festive season in the bush",
     "text": "The herds arrive in the southern Serengeti and the plains fill with life. A popular time to celebrate "
             "Christmas on safari or the New Year on Uhuru Peak."},
]
