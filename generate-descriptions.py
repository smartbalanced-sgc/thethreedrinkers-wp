#!/usr/bin/env python3
"""
Generate meta descriptions for:
  1. 39 articles with missing or useless descriptions
  2. 293 high-traffic tags (>=100 clicks) with no descriptions
  3. Auto-truncate 713 articles with descriptions >176 chars

All descriptions written by Claude in this session — no API calls needed.
Output: descriptions-final.csv (import-ready for WP-CLI script)
"""
import csv, re, html
from urllib.parse import unquote

# ============================================================
# ARTICLE DESCRIPTIONS (39 articles — from WXR content)
# ============================================================
ARTICLE_DESCS = {
"the-worlds-best-sipping-tequilas":
    "Tequila isn't just for shots. Aidy Smith picks the world's finest sipping tequilas — smooth, complex bottles worth savouring slowly.",

"strawberry-gin-sour-recipe":
    "Aidy's strawberry gin sour is simple, stunning and seriously impressive. Three ingredients, two minutes, one beautiful cocktail.",

"whisky-infused-with-a-severed-human-toe-anyone":
    "In Yukon, Canada, a bar demands your lips touch a real severed human toe. Helena Nicklin investigates the legendary Sourtoe Cocktail.",

"the-best-drinks-with-curry":
    "Beer, wine or cocktails with your curry? Helena Nicklin's essential guide to the best drink pairings for every curry dish on the menu.",

"which-is-the-driest-style-of-prosecco-guide-to-prosecco-styles":
    "Extra Brut, Brut, Extra Dry, Dry — Prosecco labels confuse everyone. Helena Nicklin decodes every sweetness level so you know exactly what you're buying.",

"the-best-luxury-rums":
    "Colin Hampden-White selects the finest luxury rums worth seeking out — aged, complex bottles that prove rum is every bit as sophisticated as whisky.",

"glenmorangie-its-kind-of-delicious-and-wonderful":
    "Colin Hampden-White visits Glenmorangie in the Scottish Highlands, exploring why this constantly experimenting distillery makes extraordinary whisky.",

"best-spanish-wine-region-carinena":
    "Helena Nicklin explores Cariñena — Spain's best-kept wine secret, with ancient vines, extraordinary history and bottles that punch well above their price.",

"best-bang-for-buck-sipping-bourbon":
    "Great bourbon doesn't have to cost a fortune. Colin Hampden-White picks the best value sipping bourbons with real flavour at sensible prices.",

"3-reasons-to-love-the-small-beer-brew-co":
    "Small Beer Brew Co is rewriting what a session beer can be. Helena Nicklin explains why their low-ABV lagers are genuinely worth drinking.",

"4-best-rums-around-the-world":
    "From the Caribbean to Central America, Aidy Smith picks four outstanding rums that show exactly why this spirit has never been more exciting.",

"5-genius-inventions-to-help-you-lose-weight":
    "Lockdown added the kilos. Aidy Smith rounds up five genuinely clever inventions to help you get back on track without giving up the good stuff.",

"a-tamdhu-attitude":
    "Tamdhu is one of Speyside's most underrated distilleries. Colin Hampden-White on why their sherry-cask whiskies are well worth discovering right now.",

"best-american-whiskies-to-discover-whiskey-whisky-bourbon-rye":
    "From bourbon to rye, Aidy Smith's guide to the best American whiskeys — shaped by years living in California surrounded by great bottles.",

"best-beer-lager-new-beers":
    "Six modern, marvellous beers with great stories. Helena Nicklin rounds up the latest craft releases worth trying for International Beer Day.",

"best-boxed-wine-bag-in-box-wine":
    "Bag-in-box wine has had a serious upgrade. Helena Nicklin makes the case with eight convincing reasons even wine snobs should give it a try.",

"best-flavoured-gin-for-spring":
    "Not all flavoured gins suit every season. Colin Hampden-White picks the best flavoured gins to pour when the evenings get lighter and spring arrives.",

"best-non-alcoholic-drinks-2021":
    "Drinking less but better? Aidy Smith's pick of the best no and low alcohol drinks in 2021 — genuinely impressive alternatives that actually taste great.",

"best-smoked-salmon-spirit-pairing":
    "Smoked salmon and whisky is one of food and drink's great partnerships. Colin Hampden-White explores Campbell's remarkable spirit-cured salmon range.",

"best-wine-finished-whiskies":
    "Move beyond ex-bourbon casks. Colin Hampden-White picks the best wine-finished whiskies where a final cask adds complexity you can't get any other way.",

"five-best-vodkas-under-25":
    "Great vodka doesn't need to be expensive. Colin Hampden-White, a World Vodka Awards judge, picks the purest, most characterful vodkas under £30.",

"great-winter-rose-wines-best-pink-wine":
    "Rosé isn't just for summer. Helena Nicklin's pick of four winter rosés that hold their own against reds with roasts, cheese boards and Christmas feasts.",

"if-world-leaders-were-drinks":
    "If world leaders were drinks, which bottle would each be? Colin Hampden-White's witty and surprisingly accurate guide to politics through the glass.",

"it-london-review-best-london-bars":
    "IT London in Mayfair delivers one of the capital's most impressive cocktail menus in a genuinely beautiful setting. Here's what to order.",

"lvmh-increases-american-whiskey-portfolio-by-investing-in-whistlepig":
    "LVMH has taken a stake in Vermont's WhistlePig. Aidy Smith on what it means for one of America's most exciting rye whiskey brands.",

"marvellous-malbecs-under-15-for-malbec-day":
    "World Malbec Day sorted. Helena Nicklin picks the best velvety, chocolatey Malbecs under £15 — the grape that made Argentina's wine reputation.",

"one-minute-wine-ace-pinot-noir":
    "Pinot Noir is the most temperamental but beautiful of red grapes. Helena Nicklin's quick guide covers everything you need to know in under a minute.",

"one-minute-wine-ace-sauvignon-blanc":
    "The Marmite of white wines. Helena Nicklin's quick guide to Sauvignon Blanc — cut grass, gooseberry and nettles — and exactly why you should love it.",

"rasteau-aoc-wine-guide-rhone-french-wine":
    "Rasteau AOC is one of the Rhône Valley's star appellations. Helena Nicklin explains why this southern French wine region is one of France's best secrets.",

"rose-grapefruit-cocktail":
    "Rosé wine, grapefruit juice, a touch of sparkle. Aidy Smith's elegant cocktail is the kind of thing you'll want to make every warm evening all summer.",

"s22f95a7wciwfeog8xh16bddl4ql7s":
    "Test your wine knowledge with The Three Drinkers. From grapes to regions, find out how much you really know about the world's most popular drink.",

"simply-whisky":
    "Independent bottlers are whisky's best secret. Colin Hampden-White explores Simply Whisky — an independent bottler that genuinely cares about quality.",

"the-last-drop-distillers-the-worlds-best-spirits-collection":
    "The Last Drop Distillers sources the world's rarest, oldest spirits. Aidy Smith on why this extraordinary collection represents the pinnacle of the craft.",

"the-most-expensive-low-alcohol-wine-in-the-world":
    "Royal Tokaji Essencia is just 4% ABV but sells for thousands. Colin Hampden-White on why this extraordinary Hungarian wine with 500g/L sugar is worth it.",

"the-story-of-city-of-london-distillery":
    "The City of London Distillery found a home in the Square Mile and started making some of London's most interesting gins. Here's the full story.",

"two-stories-you-never-knew-about-the-royal-family-and-wine":
    "Two wine stories from the Royal Family that most people have never heard. Aidy Smith uncovers the monarch's surprising relationship with British wine.",

"wakefield-wines-jaraman-cabernet-sauvignon":
    "Wakefield Wines is the world's most awarded winery — and still family owned. Aidy Smith reviews the Jaraman Cabernet Sauvignon and tells their story.",

"what-is-rye-whiskey-and-what-should-i-buy":
    "American rye or Canadian whisky? Colin Hampden-White explains what rye whiskey actually is, how it differs from bourbon, and which bottles to try first.",

"why-sweet-bordeaux-amp-cocktails-are-the-perfect-match":
    "Sweet Bordeaux and cocktails are a surprisingly perfect match. Aidy Smith explains why white and dessert Bordeaux wines belong in your cocktail shaker.",
}

# ============================================================
# TAG DESCRIPTIONS (293 tags with >= 100 GSC clicks)
# ============================================================
TAG_DESCS = {
# --- ADULTS-ONLY SOFT PLAY ---
"adults-only soft play centre birmingham":
    "The best adults-only soft play bars in Birmingham — honest venue reviews to help you book the perfect night out with slides, ball pits and cold drinks.",
"adults-only soft play centre  nottingham":
    "The best adults-only soft play bars in Nottingham — honest venue reviews so you know exactly where to book for a fun night out with your group.",
"adults-only soft play centre  newcastle":
    "The best adults-only soft play bars in Newcastle — reviewed honestly so you can pick the right venue for a seriously fun night out.",
"adults-only soft play centre  edinburgh":
    "The best adults-only soft play bars in Edinburgh — honestly reviewed so you know exactly where to take your group for a genuinely great night.",
"adults-only soft play centre  bristol":
    "The best adults-only soft play bars in Bristol — honest reviews so you know exactly where to book for slides, ball pits and plenty of drinks.",
"adults-only soft play centre  cardiff":
    "The best adults-only soft play bars in Cardiff — honest reviews of every venue worth visiting for a different kind of night out with drinks.",
"adults-only soft play centre  hull":
    "The best adults-only soft play bars in Hull — honest reviews of every venue worth booking for a different kind of night out.",
"adults-only soft play centre  bath":
    "The best adults-only soft play bars in Bath — honest venue reviews to help you find the right spot for a fun night out with friends.",
"adults-only soft play centre london":
    "The best adults-only soft play bars in London — from east to west, honest reviews of every venue worth booking for your group.",
"adults-only soft play centre  2024":
    "The best adults-only soft play bars across the UK in 2024 — honest reviews of venues worth booking for a brilliantly fun night out.",
"soft play":
    "Everything The Three Drinkers have written about adults-only soft play bars — venue reviews, city guides and what to expect at the UK's best spots.",

# --- HOW LONG DOES X LAST? ---
"How long does Whisky & Brandy last?":
    "Whisky and brandy don't last forever once opened. Here's exactly how long they stay at their best and how to store them to get every last drop.",
"How long does Vermouth last?":
    "Vermouth goes off faster than you think. Here's exactly how long it lasts once opened, how to store it, and whether yours is still good.",
"How long does it take to cool beer in the freezer?":
    "Freezer, fridge or ice bucket — which cools beer fastest? Here's the definitive answer on exactly how long your beer needs in the freezer.",
"Which Prosecco is sweet?":
    "The sweetness levels on Prosecco labels are genuinely confusing. Here's a plain-English guide to which styles are sweet, dry and everything between.",
"is lidl vodka good?":
    "Is Lidl's own-label vodka actually worth buying? Here's an honest verdict on whether Hortus and other Lidl vodkas are genuinely good or just cheap.",
"does baileys go in the fridge":
    "Does Baileys need to be refrigerated? Here's the definitive answer on how to store it, how long it lasts and whether yours is still good.",
"How long does Baileys/Advocaat last?":
    "Baileys and Advocaat both contain dairy — so how long do they last? Here's exactly what to expect from an open bottle and how to store it properly.",
"How long does Malibu last?":
    "Malibu lasts longer than you might expect, but it does go off. Here's exactly how long it stays good once opened and the best way to store it.",
"How long does Baileys last?":
    "Baileys has a surprisingly long shelf life — but it's not forever. Here's exactly how long it keeps once opened and the signs it's gone off.",
"How long does Vodka last?":
    "Vodka is one of the most stable spirits you can buy — but does it actually last forever? Here's the honest answer on vodka's shelf life.",
"How long does Rum last?":
    "Rum is a robust spirit but it does change over time once opened. Here's exactly how long rum lasts and the best way to store your bottles.",
"How long does Port last?":
    "Port has a very different shelf life depending on the style. Here's how long each type of Port lasts once opened and how to store it properly.",
"How long does vermouth keep once the bottle is opened?":
    "Opened vermouth goes stale fast. Here's exactly how long each style lasts in the fridge and the one storage mistake that ruins most bottles.",

# --- COCKTAIL TYPES & RECIPES ---
"stirred cocktail recipes":
    "Every stirred cocktail recipe you need — Martinis, Manhattans, Negronis, Old Fashioneds and more. Step-by-step guides with tips on ice and technique.",
"best cocktails to make with cremant":
    "Crémant makes a brilliant cocktail base that most people overlook. Here are the best cocktails to make with crémant — elegant, affordable and fizzy.",
"best cocktails to make with Cava":
    "Cava is one of the best-value cocktail ingredients you can buy. Here are the most impressive cocktails to make with Cava, from spritzes to punches.",
"Exotic Cocktails":
    "Beyond the classic cocktail list — here are the most exotic and unusual cocktails worth making at home, from tiki drinks to forgotten classics.",
"Which cocktails are in the Daisy family?":
    "Margaritas, Sidecars and more all belong to the Daisy family. Here's every cocktail in this classic group, with recipes and what links them all.",
"Hot alcoholic drinks":
    "Hot cocktails deserve more love. Here are the best hot alcoholic drinks to make — from Irish Coffee to mulled wine and everything in between.",
"Classic cocktail families":
    "Most cocktails belong to a small number of classic families. Here's how to understand cocktail construction by mastering the families first.",
"DIY cocktails with Hooch":
    "Hooch is back — and it makes surprisingly good cocktails. Here are the best DIY cocktail recipes to try with the iconic alcopop.",
"RHUBARB & CUSTARD COCKTAIL":
    "Rhubarb and custard in cocktail form — here's the recipe for this nostalgic, beautifully balanced drink that's easier to make than it sounds.",
"Aperol Sbagliato":
    "The Sbagliato is an accidental masterpiece. Here's the recipe for this Italian spritz with Aperol, prosecco and a splash of sweet vermouth.",
"irn bru cocktails":
    "IRN-BRU is one of Scotland's most versatile mixers. Here are the best cocktails to make with it — sweet, fizzy and genuinely brilliant.",
"grand marnier pancakes recipe":
    "Grand Marnier transforms ordinary pancakes into something extraordinary. Here's the recipe for the most indulgent, boozy pancake stack you've ever made.",
"Vermouth spritz recipe":
    "A vermouth spritz is one of the most refreshing, low-ABV cocktails you can make. Here's the recipe and the best vermouth to use.",
"Spicy Tommy's Margarita recipe":
    "Tommy's Margarita is already the best Margarita — add chilli and it becomes something extraordinary. Here's the recipe for a spicy version.",
"The Brigadoon Cocktail recipe":
    "The Brigadoon cocktail is a beautifully smoky, complex Scotch-based drink. Here's the full recipe with all the ingredients and the technique.",
"nolly prat cocktail":
    "Noilly Prat is one of the world's great vermouths. Here are the best cocktails to make with it, from classic Martinis to unexpected combinations.",
"Alternatives to Pimm's No. 1":
    "Not a Pimm's fan, or just want to try something different? Here are the best alternatives to Pimm's No. 1 — some better, some just different.",
"Pimm's alternatives":
    "There are brilliant alternatives to Pimm's that most people have never tried. Here are the best bottles to use instead for a summer jug of something special.",
"Are there really only five original cocktails?":
    "The theory says every cocktail is a variation of just five originals. Here's what they are, whether it's true and how every drink traces back to them.",
"How does a Caipirinha differ from a Daiquiri?":
    "Both are rum-adjacent, both are refreshing — so what actually separates a Caipirinha from a Daiquiri? Here's the full breakdown.",
"burnt martini":
    "The burnt martini is a dramatic twist on the classic. Here's how to make it, what to smoke it with and why it works so well.",

# --- SPIRITS KNOWLEDGE ---
"How Does VS Cognac differ to VSOP and XO Cognac?":
    "VS, VSOP and XO mean very different things on a Cognac label. Here's exactly what each grade means and which to buy depending on your budget.",
"How Does XO Cognac differ to VSOP and XXO Cognac?":
    "XO Cognac is the pinnacle — but what separates it from VSOP, and what does XXO mean? Here's a plain-English guide to Cognac grades.",
"what is the best xo cognac":
    "The best XO Cognacs are extraordinary — and very different from each other. Here's a guide to the finest bottles and what makes each one special.",
"Which VSOP Cognac should I try?":
    "VSOP Cognac is the sweet spot between price and quality. Here are the best VSOP bottles to buy right now, from well-known houses to hidden gems.",
"coke and cognac":
    "Cognac and cola is a combination that sounds wrong until you try it. Here's everything you need to know about mixing Cognac with Coke.",
"cola and cognac":
    "Cola and Cognac is an underrated, surprisingly elegant combination. Here's the best way to make it and which Cognac to use.",
"best brandy under £50":
    "You don't need to spend a fortune on great brandy. Here are the best bottles under £50 — from Armagnac to Cognac to lesser-known gems worth finding.",
"best Calvados under £60":
    "Calvados is one of France's most underappreciated spirits. Here are the best bottles under £60 — aged, complex and perfect in cocktails or neat.",
"Is Squealing Pig Sauvignon Blanc any good?":
    "Squealing Pig is everywhere — but is it actually good? Here's an honest review of the Sauvignon Blanc that became one of the UK's bestselling wines.",
"is poitin like vodka?":
    "Poitín is Ireland's original white spirit — but is it really just vodka? Here's exactly what makes it different and what it actually tastes like.",
"what does poitin taste like?":
    "Poitín tastes unlike anything else you've tried. Here's an honest description of the flavour, how it's made and the best bottles to try first.",
"What does Mead taste like?":
    "Mead is having a revival — but if you've never tried it, here's exactly what it tastes like, how sweet it is and which bottle to try first.",
"Is gin just flavored vodka":
    "It's a question that annoys gin lovers everywhere — but is there actually any truth to it? Here's the honest, definitive answer.",
"Is gin stronger than vodka?":
    "Gin and vodka are usually the same ABV — so which is actually stronger? Here's the real answer and what actually makes them so different.",
"Neutral vs characterful vodka":
    "Some vodkas are meant to taste of nothing. Others have real character. Here's the difference and which style you should actually be buying.",
"8 Seriously Smooth Vodkas You Need To Try":
    "The smoothest vodkas are the ones that slip past you dangerously easily. Here are eight genuinely smooth bottles worth tracking down and trying.",
"8 Seriously Smooth Vodkas You Need To Try the three drinkers":
    "The smoothest vodkas are the ones you barely notice you're drinking. Here are eight of the most dangerously smooth bottles to try right now.",
"what is the best gin in uk supermarket?":
    "The UK's supermarkets now stock genuinely excellent gins at great prices. Here's which supermarket gin is actually worth buying right now.",
"best budget gin":
    "Great gin doesn't need to be expensive. Here are the best budget gins that genuinely deliver — no compromise on botanicals or flavour.",
"Hortus London Dry Gin":
    "Lidl's Hortus London Dry Gin is one of the UK's best-value bottles. Here's an honest review of whether it's actually as good as the hype says.",
"Which Whitley Neill Gin is the most popular":
    "Whitley Neill makes a vast range of flavoured gins. Here's a guide to the most popular, what makes each one different and which to buy first.",
"Is Another Hendrick's gin worth trying":
    "Hendrick's keeps launching new expressions — but are they worth the premium? Here's an honest verdict on whether Another Hendrick's earns its place.",
"How do you make an Another Hendrick's spritz":
    "Another Hendrick's makes a beautiful spritz. Here's the recipe — what to pair it with, how much to pour and which garnish works best.",
"does sparkling water go with gin":
    "Sparkling water as a gin mixer sounds too simple — but is it actually good? Here's an honest verdict and when to use it instead of tonic.",
"if i don't like tonic what should i drink with gin":
    "Hates tonic water but loves gin? Here are the best alternatives — from soda to ginger ale to elderflower — that work beautifully with different gin styles.",
"best tonic water for a gin and tonic":
    "The tonic makes or breaks a gin and tonic. Here's a definitive guide to the best tonic waters and which one to pair with your particular gin.",
"What Are The Different Flavours of Tonic Water?":
    "Tonic water now comes in dozens of flavours. Here's a guide to the most useful styles — Mediterranean, elderflower, light and more — and when to use each.",
"which tonic water is the best":
    "Not all tonic water is the same. Here's an honest ranking of the best tonic waters available in the UK, from supermarket shelves to premium bottles.",
"7 Affordable Tequilas Perfect For Margaritas uk":
    "A Margarita lives or dies by the tequila. Here are seven affordable bottles that make genuinely excellent Margaritas without breaking the bank.",
"Should you use Blanco or Reposado tequila in a Margarita?":
    "It's one of the great Margarita debates. Here's the definitive answer on whether Blanco or Reposado tequila makes the better cocktail.",
"what is the best budget tequila to use in margarita?":
    "The best Margaritas don't require expensive tequila. Here are the best budget bottles for the job — genuinely good tequilas at honest prices.",
"Can I use bottled lime juice in a Margarita?":
    "Fresh lime vs bottled juice in a Margarita — does it actually matter? Here's an honest answer and when bottled juice is genuinely good enough.",
"what are the best tequila cocktails to make without a shaker?":
    "No cocktail shaker? No problem. Here are the best tequila cocktails you can make without one, using just a glass, a spoon and the right ice.",
"What juices mix well with rum?":
    "Rum is one of the most mixer-friendly spirits there is. Here are the best juices to pair with rum — from pineapple to mango to orange.",
"Rum and tonic water":
    "Rum and tonic water is a surprisingly refreshing combination that most people have never tried. Here's how to make it and which rum to use.",
"Rum and orange juice":
    "Rum and orange juice is a classic, underrated combination. Here's the best way to make it, which rum to use and how to take it further.",
"Rum and lemonade":
    "Rum and lemonade is one of the simplest, most refreshing long drinks you can make. Here's the best rum to use and how to build the perfect serve.",
"Rum and ginger beer":
    "Rum and ginger beer is a combination that works brilliantly. Here's the best rum to use, the right ratio and how to make the perfect Dark and Stormy.",
"which rum goes with tea?":
    "Rum and tea is a combination with deep roots and real flavour logic. Here's which rums pair best with different tea styles.",
"which tea goes with rum?":
    "The right tea makes rum into something special. Here's which teas work best with rum, why the combination works and how to make the perfect serve.",
"Which Country Produces the Most Rum?":
    "The answer might surprise you. Here's a full breakdown of global rum production by country — and which nation actually makes the most.",
"rum producing countries":
    "Rum is made everywhere from the Caribbean to Australia. Here's a guide to every major rum-producing country and what makes each one's style distinct.",
"Best cachaça for Caipirinha":
    "The Caipirinha lives and dies by its cachaça. Here are the best bottles to use, from budget bottles to premium options worth the extra spend.",
"Best cachaça brands":
    "Cachaça is far more varied than most people realise. Here's a guide to the best cachaça brands available in the UK — from grassy to complex.",
"Singani Sour (Bolivia)":
    "Singani is Bolivia's national spirit and makes an extraordinary Sour. Here's everything about this grape-based spirit and the recipe to try.",
"Horchata Con Ron (El Salvador)":
    "Horchata Con Ron is El Salvador's most beloved drink — sweet, spiced and surprisingly complex. Here's the recipe and what makes it so special.",
"Rakija Sour (Serbia) guide":
    "Rakija is the Balkans' most beloved spirit and makes a brilliant Sour. Here's a guide to Serbian Rakija and the definitive Rakija Sour recipe.",
"what are the rum cocktails to make without a shaker?":
    "No cocktail shaker? These rum cocktails are built directly in the glass — no shaking, no straining, just great drinks made simply.",
"What drink is Casablanca known for?":
    "Casablanca has a rich cocktail culture tied to its past. Here's the drink the city is famous for, its history and where to find the best version.",
"What drink is Mad Men known for?":
    "Mad Men made certain drinks iconic. Here's the drink most associated with the show, why Don Draper drank it and how to make it at home.",
"What do they drink in Sex and the City?":
    "Sex and the City made the Cosmopolitan famous — but the characters drank a lot more than that. Here's the full drinks menu from all six seasons.",
"What drink is The Great Gatsby known for?":
    "The Great Gatsby is soaked in Champagne and excess. Here's the drink most associated with the novel, the film and how to recreate the era.",
"What drink is in The Queen's Gambit?":
    "The Queen's Gambit has a surprisingly specific relationship with alcohol. Here's what Beth Harmon drinks and the cocktails most associated with the show.",
"what does james bond drink in the books?":
    "James Bond's drinks in Ian Fleming's novels are very different from the films. Here's exactly what 007 orders across all the original books.",
"why does james bond order his martini shaken not stirred?":
    "It's one of fiction's most famous drink orders — and there's an actual reason for it. Here's why Bond orders his Martini shaken, not stirred.",
"what is the first drink james bond orders?":
    "James Bond's very first drink order in the books surprises most people. Here's what it was, in which book it appears and what it reveals about the character.",
"what is the first drink daniel craig orders as james bond?":
    "Daniel Craig's Bond has very different tastes from his predecessors. Here's the first drink the new 007 orders on screen and what it says about the character.",
"james bond's favourite drinks":
    "James Bond's drinks order varies across films and books. Here's a complete guide to every drink Bond is known for — from the Vesper to the Martini.",
"what alcohol does king charles drink?":
    "King Charles has well-documented preferences when it comes to alcohol. Here's what the King drinks, his favourite spirits and the brands he's associated with.",
"Prince's favourite cocktail":
    "Prince had very specific tastes — including in drinks. Here's the cocktail most associated with him and why it suited his aesthetic perfectly.",
"Dubonnet":
    "Dubonnet is a fortified wine with a remarkable royal history. Here's what it tastes like, how to drink it and why the Queen was so fond of it.",

# --- WINE KNOWLEDGE ---
"what is the right glass for pinot grigio":
    "The right glass genuinely changes how Pinot Grigio tastes. Here's which glass to use, why it matters and the one shape to avoid.",
"what is the right glass for malbec":
    "Malbec needs a big bowl to breathe properly. Here's the right glass to use, why the shape matters and how it changes the drinking experience.",
"what is the right glass for rose":
    "Rosé doesn't need a special glass — but the right one makes a real difference. Here's the shape to look for and why stem length matters for rosé.",
"what is the right glass for chianti":
    "Chianti's firm tannins and acidity respond well to the right glass. Here's the shape to use and why it makes this Italian red taste noticeably better.",
"what is the right glass for sangiovese":
    "Sangiovese is a structured, acidic grape that rewards the right glass. Here's which shape brings out the best in it and why.",
"what is the right glass for zinfandel":
    "Zinfandel is big, bold and tannic — here's the right glass to use and why a larger bowl makes a meaningful difference to how it tastes.",
"what is the right glass for syrah":
    "Syrah's peppery, full-bodied character responds well to the right glass. Here's the shape to reach for and why it brings out the best in the wine.",
"what is the right glass for barolo":
    "Barolo is one of Italy's most structured wines. Here's the right glass to use, why it matters and how long to decant it before you pour.",
"what is the right glass for beaujolais":
    "Beaujolais is lighter than most reds and drinks differently. Here's the right glass for both Nouveau and more serious cru Beaujolais.",
"what is the right glass for grenache":
    "Grenache is a warm, fruity red that benefits from the right glass. Here's which shape to use and why it changes the way the wine expresses itself.",
"what is the right glass for cabernet franc":
    "Cabernet Franc has a distinctive herbal character that the right glass can enhance or diminish. Here's which shape brings out the best in it.",
"what is the right glass for orange wine":
    "Orange wine sits between white and red in style — and the right glass is somewhere between the two. Here's what works best and why.",
"what is the right glass for rioja":
    "Rioja's oak-driven character rewards the right glass. Here's the shape to use for both Crianza and Gran Reserva and why each benefits differently.",
"what is the best temperature for barolo wine?":
    "Barolo served too cold loses its complexity. Here's the right serving temperature, how long to decant it and the one mistake most people make.",
"Are Aldi's Champagnes any good?":
    "Aldi's Champagnes turn up in best-buy lists every year. Here's an honest verdict on whether they're genuinely good or just well-priced for the category.",
"best rose wines in tesco the three drinkers":
    "Tesco stocks some genuinely excellent rosé wines at honest prices. Here are the best bottles on the shelves right now.",
"best red wines asda":
    "ASDA's wine range has some real hidden gems. Here are the best red wines currently on the shelves, tried and ranked honestly.",
"best red wines in tesco the three drinkers":
    "Tesco's red wine selection spans every price point. Here are the best bottles on the shelves right now, from budget to splurge.",
"best aldi red wine":
    "Aldi's wine range punches well above its price. Here are the best red wines to buy right now from Aldi's regularly-changing shelves.",
"best aldi wines right now":
    "Aldi's wine range changes constantly. Here are the best bottles available right now — the ones worth putting in your basket immediately.",
"best aldi wines":
    "From everyday bottles to Champagne, Aldi's wine selection is consistently impressive. Here are the best buys to pick up on your next visit.",
"best value uk supermarket wines 2024":
    "The UK's supermarkets are full of genuinely good wine if you know where to look. Here are the best-value bottles across all the major chains in 2024.",
"best supermarket sparkling wine":
    "Great sparkling wine doesn't require a trip to a specialist. Here are the best bottles from UK supermarkets right now — Prosecco, Crémant and more.",
"best alternative to prosecco":
    "Prosecco is everywhere — but there are better options at similar prices. Here are the best alternatives worth switching to.",
"best rated wines in tesco 2024":
    "The best wines in Tesco right now, across every style and price point — tried, tasted and honestly reviewed for 2024.",
"best supermarket ciders":
    "The UK's supermarkets stock a surprising range of excellent cider. Here are the best bottles and cans to pick up on your next shop.",
"sainsbury's best wines":
    "Sainsbury's wine range has some genuine standouts. Here are the best bottles across all styles and price points available right now.",
"best waitrose wines this christmas":
    "Waitrose's Christmas wine range is consistently one of the best on the high street. Here are the bottles worth buying for the festive season.",
"best white wines in tesco":
    "Tesco's white wine selection has something for every budget. Here are the best bottles on the shelves right now.",
"best white wines asda":
    "ASDA's white wine range spans every style and price point. Here are the best bottles on the shelves right now.",
"best white chocolate liqueurs":
    "White chocolate liqueurs range from cloyingly sweet to genuinely delicious. Here are the best bottles available in the UK right now.",
"Tesco Finest Prosecco Valdobbiadene DOCG":
    "Tesco Finest Prosecco Valdobbiadene DOCG is one of the best supermarket Proseccos you can buy. Here's an honest review of whether it lives up to its label.",
"ASDA Extra Special Prosecco Rosé Brut":
    "ASDA's Extra Special Prosecco Rosé Brut is one of the supermarket category's most consistent performers. Here's an honest review.",
"Corte Alle Mura Chianti Riserva":
    "Corte Alle Mura Chianti Riserva offers serious Tuscan quality at a sensible price. Here's a full tasting note and whether it's worth buying.",
"Nicolas de Mont Bart":
    "Nicolas de Mont Bart is one of Burgundy's most reliable producers. Here's everything you need to know about the range and which bottles to try.",
"Comte de Senneval":
    "Comte de Senneval is a Champagne worth knowing about. Here's a full tasting note and honest review of this producer's key bottles.",
"terre di faiano":
    "Terre di Faiano is a Southern Italian producer making wines that over-deliver at their price point. Here's an honest review of the range.",
"best rated wines at sainsbury's":
    "The best wines at Sainsbury's right now — tried, tasted and honestly rated across every style, from under a tenner to special-occasion bottles.",
"Supermarket Wine Bargains: Sainsbury's February 2024 best wines":
    "Sainsbury's February 2024 best-value bottles — the wines worth picking up right now before they disappear from the shelves.",
"best morrisons wines march 2024":
    "The best wines at Morrisons in March 2024 — tried, tasted and honestly reviewed across every style and price point.",
"best supermarket wines under £10 morrisons":
    "Great wine under £10 at Morrisons — here are the bottles genuinely worth buying, tried and tasted honestly.",
"best current wine offers in morrisons":
    "The best wine deals at Morrisons right now — the bottles offering the best value across every style and price point.",
"best port subscriptions":
    "Port subscriptions deliver extraordinary value if you choose the right one. Here are the best Port subscription boxes available in the UK right now.",
"what should i pair with sticky toffee pudding":
    "Sticky toffee pudding needs the right drink to complete it. Here are the best wine, spirits and dessert drink pairings for this British classic.",
"what should i pair with cheescake":
    "Cheesecake and the right drink is a genuinely brilliant combination. Here are the best wine and drinks pairings for every style of cheesecake.",
"which crisps should i eat with rose":
    "Rosé and crisps is one of life's great simple pleasures — but the right crisp flavour makes a real difference. Here's exactly what to reach for.",
"chinese food and beer pairings":
    "Chinese food and beer pairing is an underexplored area of food and drink. Here's which beer styles work best with different Chinese dishes.",
"what should i pair with chinese food":
    "Chinese food is one of the most varied cuisines in the world — here's a guide to the best wine, beer and spirits to pair with different dishes.",

# --- GIN & WHISKY ---
"best gin cocktails to make without a shaker":
    "No cocktail shaker needed. Here are the best gin cocktails built directly in the glass — elegant, delicious and completely equipment-free.",
"what are the best gin cocktails to make without a shaker?":
    "No shaker? No problem. Here are the best gin cocktails you can make without any equipment — just a glass, some ice and the right ingredients.",
"What is the history of the Garibaldi cocktail?":
    "The Garibaldi is one of Italy's most elegant cocktails and its history is fascinating. Here's everything about this Campari and orange juice classic.",
"Best amaretto for amaretto sour":
    "The Amaretto Sour is only as good as its amaretto. Here are the best bottles to use and why the choice of amaretto makes such a big difference.",
"Best amaretto for a godfather":
    "The Godfather cocktail needs the right amaretto. Here are the best bottles to use and how the choice changes the character of this classic drink.",
"best amaretto":
    "Amaretto ranges from cheap and cloying to genuinely complex. Here are the best amaretto bottles available in the UK right now.",
"The history of Amaretto":
    "Amaretto's origin story is one of the most contested in spirits. Here's the full history — from the legend to the reality — of this Italian liqueur.",
"How is amaretto made?":
    "Amaretto is made from almonds, apricot kernels — or both. Here's how it's actually produced and what the best producers do differently.",
"amaretto sidecar":
    "The Amaretto Sidecar is a softer, sweeter take on the classic Sidecar cocktail. Here's the recipe and the amaretto to use.",
"best aniseed drinks to try":
    "Aniseed-flavoured drinks are an acquired taste that's well worth acquiring. Here are the best bottles to try, from Pastis to Sambuca to Absinthe.",
"What are the different types of Absinthe?":
    "Not all Absinthe is the same — there are genuine style differences worth understanding. Here's a guide to the main types and which to try first.",
"is amaro and bitter the same":
    "Amaro and bitters are both bitter — but they're very different things. Here's the clear explanation of what separates them.",
"best aniseed drinks":
    "From Pastis to Sambuca, aniseed spirits are experiencing a revival. Here are the best bottles to try right now across every style.",
"Which VSOP Cognac should I try?":
    "VSOP is the sweet spot in the Cognac range. Here are the best VSOP bottles to try right now — from famous houses to underrated alternatives.",
"what is the best rum to use for a daiquiri?":
    "The Daiquiri is three ingredients — so the rum matters enormously. Here's the best rum to use for a classic Daiquiri, and why it makes a difference.",
"best whiskey for whiskey sour":
    "The Whiskey Sour is forgiving but the whiskey still matters. Here are the best bottles to use for a perfect, balanced, beautifully tart Whiskey Sour.",
"What are the best rye whiskies from Europe?":
    "European rye whisky is a small but exciting category. Here are the best bottles to try — and why they're worth seeking out.",
"Which is the best sherry cask finished whisky in speyside?":
    "Sherry cask finishes are everywhere in Speyside — but the quality varies hugely. Here are the best bottles where the cask genuinely adds something.",
"which whisky should I invest in?":
    "Not all whisky appreciates in value — here's an honest guide to which bottles are worth buying as an investment and which aren't.",
"Which whisky tasting sets are best?":
    "Whisky tasting sets are the best introduction to a new distillery or style. Here are the best ones currently available and what makes each worthwhile.",
"Best scotch whisky for Christmas":
    "Christmas is the season for Scotch. Here are the best bottles to give or receive this year — for every budget and every level of whisky knowledge.",
"jura 10 cocktails":
    "Jura 10 is one of Scotland's most versatile whiskies. Here are the best cocktails to make with it — some classic, some unexpected.",
"Highland Park Cask Strength Heather review":
    "Highland Park's cask strength Heather release is one of the distillery's most interesting limited expressions. Here's a full honest review.",
"best Calvados under £60":
    "Calvados is Normandy's great spirit — apple brandy aged in oak. Here are the best bottles under £60 to try if you've never explored the category.",
"The Best Whisky Advent Calendar":
    "Whisky advent calendars range from brilliant to deeply disappointing. Here are the best ones to buy this year — ranked honestly by value and quality.",
"best tequila advent calendar":
    "Tequila advent calendars are a newer addition to the festive season — and some are excellent. Here are the best ones currently available.",
"no-lo advent calendar":
    "No and low alcohol advent calendars have genuinely improved. Here are the best alcohol-free and low-ABV advent calendars available this year.",
"alcoholic advent calendars":
    "Boozy advent calendars are now one of the best Christmas gift categories. Here are the best ones to buy this year across every spirit category.",
"Luxury wine advent calendars":
    "Luxury wine advent calendars make extraordinary Christmas gifts. Here are the best premium options available this year and what's inside each one.",
"Best wine advent calendars UK 2024":
    "The best wine advent calendars available in the UK in 2024 — ranked by value, variety and how genuinely good the wine inside actually is.",
"best prosecco advent calendar":
    "Prosecco advent calendars are an excellent way to explore different styles and producers. Here are the best ones currently available.",
"The Best Cognac Advent Calendar":
    "Cognac advent calendars introduce you to the full range of this great French spirit. Here are the best ones to buy this year.",
"The Best Tequila & Mezcal Advent Calendar":
    "Tequila and mezcal advent calendars are the most exciting development in the festive drinks market. Here are the best ones this year.",
"alcoholic secret santa ideas":
    "The best alcoholic Secret Santa gifts that won't feel lazy or generic — bottles, kits and experiences for every budget and taste.",
"The Best Alcohol Subscriptions uk":
    "Drinks subscriptions are one of the best ways to discover new bottles. Here are the best alcohol subscription boxes available in the UK right now.",

# --- FOOD, CULTURE & TRAVEL ---
"best gay drinks":
    "From Pride cocktails to LGBTQ+-owned spirits brands, here are the best drinks with genuine community credentials — and they all taste great too.",
"drinks for each country eurovision":
    "Eurovision is the perfect excuse to drink around Europe. Here's the best drink from each competing country — with recipes for the ones you can make.",
"What drink is Moulin Rouge known for?":
    "The Moulin Rouge had a very specific relationship with one drink. Here's what they served, why it became iconic and how to recreate the spirit of Paris.",
"What do bartenders mean when they say 86?":
    "\"86\" is one of the most common bar terms — but what does it actually mean? Here's the origin, the different uses and the full story behind it.",
"What does '200' mean in a bar?":
    "Bar codes are a secret language most customers never hear. Here's what '200' means when bartenders use it and the other codes worth knowing.",
"How do codes like '601' or '602' help bartenders?":
    "Bartender codes exist for a reason. Here's how numerical codes help bar teams communicate discreetly and what the most common ones actually mean.",
"What do bartender codes mean?":
    "Bartenders use a secret language of codes across the bar. Here's a guide to the most common ones and what they mean.",
"Numerical codes used in bars":
    "Bars run on a code system most customers never learn. Here's a complete guide to numerical codes used by bar staff and what each one signals.",
"Hospitality codes":
    "The hospitality industry runs on a set of insider codes. Here's a guide to the most common ones used across bars and restaurants.",
"Restaurant codes":
    "Restaurant staff use a set of codes and signals that customers rarely hear. Here's a guide to the most common ones and what they mean.",
"What is the meaning of 'In the Weeds' in bartending?":
    "\"In the Weeds\" is one of the most used phrases in the drinks industry. Here's exactly what it means and where it comes from.",
"Scotland – You can be fined two beers if you have underwear beneath yo":
    "Scotland has some genuinely strange alcohol laws. Here's the full story behind this curious legal quirk and what it actually means in practice.",
"El Salvador – Death sentence for DUI?":
    "El Salvador's drink-driving laws are among the strictest in the world. Here's the truth behind the claims and what the law actually says.",
"Bolivia – Married women can only drink one glass of wine at bars!":
    "Bolivia's law on married women and alcohol is one of the strangest on record. Here's the full story behind this unusual piece of legislation.",
"UK - It is illegal to be drunk in a pub!":
    "Being drunk in a pub is technically illegal in the UK. Here's the actual law, why it exists and whether it's ever actually enforced.",
"Do different types of alcohol get you different types of drunk?":
    "Does tequila make you aggressive? Does wine make you emotional? Here's what the science actually says about whether different drinks affect you differently.",
"should you stick to one drink all night?":
    "Sticking to one drink all night is the classic advice — but does it actually help? Here's what the evidence says about mixing drinks.",
"does mixing your drinks make you ill?":
    "The old wisdom says never mix your drinks — but is it actually true? Here's what science says about mixing alcohol and feeling worse the next day.",
"why vodka is the best drink to avoid a hangover":
    "Vodka is often said to produce the mildest hangover. Here's whether that's actually true and the science behind congeners and morning-after misery.",
"what alcohol does king charles drink?":
    "King Charles is known for his specific tastes in drinks. Here's everything known about his favourite spirits and the brands he's associated with.",

# --- SEASONAL / FESTIVE ---
"Boozy Christmas Crackers":
    "Christmas crackers with miniature spirits inside — here's a guide to the best boozy Christmas crackers available and which bottles are worth finding.",
"best cocktails for summer 2026?":
    "The best cocktails for summer 2026 — from spritz variations to tropical long drinks, here's what we're all making this summer.",
"drinking holidays uk":
    "The UK has some genuinely brilliant drinking destinations. Here are the best drinking holidays available — distillery tours, wine regions and more.",
"Halloween cocktail garnishes":
    "Halloween cocktails need the right garnish to look the part. Here are the best ideas — from smoke to gore to edible decorations that actually work.",
"best pumpkin beers uk":
    "Pumpkin beers divide opinion — but the good ones are genuinely excellent. Here are the best pumpkin beers available in the UK this autumn.",
"POPS Pimm's No.1 Frozen Cocktail":
    "Pimm's POPS frozen cocktails are a summer staple. Here's an honest review of whether they're worth buying and how they compare to the real thing.",

# --- SPECIFIC DRINKS & BRANDS ---
"Liberté Spiced Rum":
    "Liberté Spiced Rum is one of the newer arrivals in a crowded category. Here's an honest review of what it tastes like and whether it's worth buying.",
"Cassario Black Spiced Flavour with Rum":
    "Cassario Black is a spiced rum-flavoured drink that's harder to categorise than it looks. Here's an honest review of what's actually in the bottle.",
"Rachmainoff Vodka review":
    "Rachmainoff Vodka is a value-priced bottle that claims a lot. Here's an honest review of whether this Russian-style vodka delivers what it promises.",
"Puschkin Nuts & Nougat Liqueur":
    "Puschkin's Nuts & Nougat liqueur is a rich, dessert-style drink that splits opinion. Here's an honest review of whether it's worth the calories.",
"Gabyr functional beer":
    "Gabyr is a functional beer doing something unusual. Here's an honest review of what it tastes like, what it claims to do and whether it works.",
"where to buy IRN-BRU Winter BRU UK":
    "IRN-BRU Winter BRU is a seasonal release that disappears fast. Here's where to find it in the UK and whether it's actually worth hunting down.",
"Aldi Specially Selected Luxury Edition Irish Cream Liqueur":
    "Aldi's luxury Irish Cream is one of the supermarket's most talked-about festive products. Here's an honest review — is it as good as Baileys?",
"Flävar in wetherspoons":
    "Flävar has made it onto the Wetherspoons menu. Here's everything you need to know about this drink and what to expect when you order it.",
"ALDI Austin's Classic Summer Punch Spirit Drink":
    "Aldi's Austin's Classic Summer Punch is one of the supermarket's most popular summer drinks. Here's an honest review of the full-size bottle.",
"Austin's Summer Punch Aldi":
    "Aldi's Austin's Summer Punch returns every summer and sells out fast. Here's an honest review and what to pair it with.",
"Gilroy's Loft menu":
    "Gilroy's Loft has one of the most interesting drinks menus around. Here's a guide to what's on offer and the bottles worth ordering.",
"The Porter's Table Covent Garden":
    "The Porter's Table in Covent Garden is one of London's underrated drinks destinations. Here's what to order and what makes it worth a visit.",
"Tobi Masa review London":
    "Tobi Masa is a London venue with serious drinks credentials. Here's a full review of the cocktail menu and what makes it worth visiting.",
"Andre Carpentier":
    "André Carpentier is a Cognac producer worth knowing about. Here's a guide to the range, the house style and the bottles most worth trying.",
"Louis Delaunay":
    "Louis Delaunay Calvados is one of Normandy's most reliable apple spirit producers. Here's a guide to the range and which bottles to try first.",

# --- EDUCATION & KNOWLEDGE ---
"Difference between aromatised and fortified wine":
    "Aromatised and fortified wines are related but genuinely different categories. Here's a plain-English explanation of what separates them.",
"Can you drink vermouth neat?":
    "Most people only know vermouth as a cocktail ingredient — but it's perfectly good on its own. Here's how to drink vermouth neat and which to try.",
"Can you drink vermouth on its own?":
    "Vermouth doesn't need a cocktail to shine. Here's how to drink it on its own, which styles work best neat and what to serve alongside it.",
"Best vermouth for martini":
    "The vermouth in a Martini matters enormously. Here are the best vermouths for a Martini, what each one brings to the drink and which to try first.",
"Best vermouth for negroni":
    "The sweet vermouth in a Negroni shapes the whole character of the drink. Here are the best bottles to use and why they make such a difference.",
"What vermouth is best for a Martini?":
    "Martini vermouth is a personal choice — but some bottles genuinely work better than others. Here's a guide to the best options for every palate.",
"the best sweet vermouths for a negroni":
    "The sweet vermouth in your Negroni changes everything. Here's a guide to the best bottles to use and how each one shifts the drink's character.",
"Negroni vs. Martini differences":
    "Both are stirred, both are spirit-forward — so what actually separates a Negroni from a Martini? Here's the full breakdown of two cocktail classics.",
"which spirit goes with black tea?":
    "Black tea and spirits is a combination with serious potential. Here's which spirits pair best with black tea and how to build the perfect serve.",
"which spirit goes with chamomile tea?":
    "Chamomile's gentle, floral character works beautifully with certain spirits. Here's the best pairings and how to make each one.",
"are there alcoholic drinks that contain tea?":
    "Tea-based alcoholic drinks are a genuinely exciting category. Here's a guide to the best bottles, brands and styles that combine tea and alcohol.",
"What is the difference between champagne and crémant?":
    "Both are French sparkling wines — but they're made very differently. Here's exactly what separates Champagne from Crémant and whether it matters.",
"Which cremant should I buy?":
    "Crémant is one of the best-value wine categories in France. Here's a guide to every style — from Alsace to Bordeaux — and which to buy first.",
"What are the 8 appellations for crémant?":
    "Crémant is made in eight distinct French regions and they taste very different. Here's a guide to every appellation and what makes each one unique.",
"Which areas of France make crémant?":
    "France makes Crémant in eight different regions — each with a different grape and a different style. Here's a guide to where each one comes from.",
"best cocktails to make with cremant":
    "Crémant makes an exceptional cocktail base that most people never think to use. Here are the best recipes — from spritzes to French 75 variations.",
"What's a good alternative to Dom Pérignon?":
    "Dom Pérignon is extraordinary — but there are bottles that come close for a fraction of the price. Here are the best alternatives worth trying.",
"which plum wine to buy":
    "Plum wine ranges from sickly sweet to genuinely complex. Here's a guide to the best bottles available in the UK and how to drink each one.",
"Wormwood wine":
    "Wormwood wine is one of the oldest and most misunderstood drink categories. Here's everything you need to know about what it is and how it tastes.",
"is pinot noir healthy?":
    "Pinot Noir is often cited as the healthiest red wine. Here's what the evidence actually says about resveratrol, polyphenols and wine and health.",
"what is the best cheese pairing for tempranillo":
    "Tempranillo's earthy, leathery character has natural affinity with certain cheeses. Here's the ideal pairing and why it works so well.",
"What drink is Casablanca known for?":
    "Casablanca has a rich cocktail culture tied to its history. Here's the drink the city is most associated with and where to find the best version.",
"What do Chinese people drink?":
    "Chinese drinking culture is extraordinarily rich and varied. Here's a guide to the most important drinks — from Baijiu to tea to craft beer.",
"Do Chinese people drink sake?":
    "Sake is Japanese — so why do some people associate it with Chinese culture? Here's the truth about sake's origins and what China actually drinks.",
"What alcohol do Chinese people drink?":
    "Baijiu, huangjiu, beer and more — Chinese drinking culture is far more varied than most people realise. Here's a full guide.",
"vagina beer":
    "It exists. A Polish brewery made it. Here's the full story behind the world's most controversial beer and whether it's actually any good.",
"rude named drinks":
    "The drinks world has an extraordinary collection of rudely named bottles. Here are the best ones — wines, spirits and beers that'll raise an eyebrow.",
"The 8 Rudest Wines You Can Buy uk":
    "Some winemakers have clearly had a sense of humour when naming their bottles. Here are the rudest wine names you can actually buy in the UK.",
"Rude Wine Names UK":
    "The UK's off-licences are full of wines with names that'll make you look twice. Here are the best and rudest wine labels you can actually buy.",
"8 Unusual Alcoholic Drinks That Actually Taste Good uk":
    "Strange ingredients, unusual methods — some truly weird drinks are also genuinely delicious. Here are eight to try if you're feeling adventurous.",
"8 Unusual Alcoholic Drinks That Actually Taste Good the three drinkers":
    "The weirdest drinks are sometimes the best ones. Here are eight genuinely unusual alcoholic drinks that actually taste extraordinary.",
"strange alcoholic drinks":
    "The world of alcohol contains some genuinely bizarre creations. Here are the strangest drinks you can actually buy — and the ones worth trying.",
"weird beer flavours":
    "Craft brewers put almost anything into beer these days. Here are the most unusual beer flavours that actually work — and a few that really don't.",
"Funny Wine Names":
    "Some winemakers are clearly having fun. Here's a collection of the funniest, most creative wine names — for when the label is half the reason you buy it.",
"Best Funny Wine Names":
    "The best funny wine names in the UK right now — genuinely witty labels that are also worth buying for what's inside the bottle.",
"funny wine labels":
    "A funny label doesn't guarantee good wine — but these ones deliver on both. Here are the best funny wine labels you can actually buy in the UK.",
"Down Under's Finest: 8 Australian Drinks You Need to Try":
    "Australia makes world-class wine, beer and spirits that most people never explore. Here are eight Australian drinks genuinely worth seeking out.",
"How to use ice buckets for chilling":
    "Ice buckets chill faster than you think — if you use them correctly. Here's exactly how to use an ice bucket to get your wine or beer cold quickly.",
"should you add salt to your ice bucket?":
    "Adding salt to an ice bucket speeds up chilling dramatically. Here's exactly how it works and the right technique to chill a bottle in minutes.",
"How do you use a wet paper towel to chill beer?":
    "The wet paper towel trick chills beer remarkably fast. Here's exactly how to do it and why it works better than it has any right to.",
"How Does salt water help in chilling drinks?":
    "Salt water chills drinks faster than ice alone. Here's the science behind it and the exact technique to chill a bottle of wine in under ten minutes.",
"How do I avoid exploding bottles in the freezer?":
    "Forgotten a bottle in the freezer? Here's exactly how long different drinks take to freeze, the warning signs and how to chill without the risk.",
"can you use a protein shaker instead of a cocktail shaker?":
    "In a pinch, a protein shaker can absolutely double as a cocktail shaker. Here's how to use one properly and what to watch out for.",
"what is a reverse dry shake?":
    "The reverse dry shake is a technique that changes the texture of cocktails with egg white. Here's exactly how to do it and why it works.",
"What are the best Pinot Noir wines under £20?":
    "Great Pinot Noir under £20 requires knowing where to look. Here are the best bottles currently available — elegant, complex and honestly priced.",
"which cream liqueur is the best?":
    "Cream liqueurs range from exceptional to overly sweet. Here's an honest ranking of the best bottles available in the UK right now.",
"best irish cream liqueur":
    "Baileys isn't the only Irish Cream worth buying. Here's a guide to the best Irish Cream liqueurs available right now — and the ones to avoid.",
"Baileys alternatives":
    "Looking for something like Baileys but different? Here are the best alternatives — some better, some just different, all worth trying.",
"what is Alcarelle":
    "Alcarelle is an alcohol alternative designed to mimic the effects of alcohol without the downsides. Here's what it actually is and how it works.",
"What is the best orange-flavoured vodka?":
    "Orange vodka ranges from artificially sweet to genuinely sophisticated. Here are the best bottles available in the UK right now.",
"Edinburgh":
    "Edinburgh is one of the world's great drinking cities. Here's everything The Three Drinkers have written about its bars, distilleries and drinks scene.",
"visit grand marnier":
    "Grand Marnier's home in the Loire Valley is well worth a visit. Here's everything you need to know about visiting the distillery and what to expect.",
"wetherspoons top trumps":
    "Wetherspoons has an extraordinary range for the price. Here's how the menu stacks up in a top trumps-style guide to the best and worst options.",
"The Best Gins For A Negroni the three drinkers":
    "The gin you use in a Negroni shapes the whole drink. Here are the best gins to use — from London Dry classics to more aromatic alternatives.",
"Louis Delaunay":
    "Louis Delaunay makes some of Normandy's most reliable Calvados. Here's a guide to the range and the bottles most worth seeking out.",
"Neutral vs characterful vodka":
    "Some vodkas want to disappear into a cocktail. Others demand attention. Here's the difference between neutral and characterful vodka styles.",
"What are the best piscos for a pisco sour":
    "The Pisco Sour is nothing without great Pisco. Here's a guide to the best bottles to use — Peruvian, Chilean and everything in between.",
"best boxed wine":
    "Bag-in-box wine has genuinely improved. Here are the best boxed wines available in the UK right now — better value per glass than almost any bottle.",
"How long does vermouth keep once the bottle is opened?":
    "Opened vermouth needs proper storage or it goes stale fast. Here's exactly how long it keeps in the fridge and the right way to store it.",
"What is the best garnish for an Aperol Spritz?":
    "The garnish on an Aperol Spritz matters more than people think. Here's the best garnish for the classic serve and alternatives worth trying.",
"Does UK make Bourbon whiskey?":
    "American Bourbon law is strict about geography — so can the UK actually make it? Here's the legal answer and what British distillers make instead.",
"Which Port is Best for a Port and Tonic?":
    "Port and tonic is one of the best long drinks nobody talks about. Here's which Port style works best, the right ratio and how to make the perfect serve.",
"best alternative to prosecco":
    "Crémant, Cava, English sparkling — there are genuinely better alternatives to Prosecco at similar prices. Here's what to try instead.",
"best supermarket sparkling wine":
    "UK supermarkets stock some genuinely excellent sparkling wines. Here are the best bottles to pick up right now — Prosecco, Crémant and beyond.",
"how to make pancakes with alcohol":
    "Adding alcohol to pancakes is a genuinely good idea. Here are the best ways to incorporate spirits, liqueurs and beer into your Pancake Day batter.",
"what is the best cheese pairing for tempranillo":
    "Tempranillo's earthy, savoury character makes it one of the most food-friendly reds. Here's the ideal cheese pairing and why it works.",
}

# Load augmented CSV
with open('/tmp/aug/seo-meta-augmented.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Build lookup by slug
by_slug = {}
for r in rows:
    slug = r['slug']
    if slug:
        by_slug[slug] = r

# Build lookup by tag name (decoded)
by_tag_name = {}
for r in rows:
    if r['url_type'] == 'tag':
        raw = r['url'].split('/tag/')[-1].rstrip('/')
        from urllib.parse import unquote
        decoded = unquote(raw).replace('+', ' ')
        by_tag_name[decoded] = r

# --- AUTO-TRUNCATE HELPER ---
def smart_truncate(text, max_len=160):
    """Truncate at last sentence boundary before max_len, fallback to last word."""
    if len(text) <= max_len:
        return text
    candidate = text[:max_len]
    # Try sentence boundary
    for sep in ['. ', '! ', '? ', '; ']:
        pos = candidate.rfind(sep)
        if pos > 80:
            return candidate[:pos+1].strip()
    # Fallback: last word boundary
    pos = candidate.rfind(' ')
    if pos > 80:
        return candidate[:pos].rstrip('.,;:') + '.'
    return candidate[:max_len-3] + '...'

# Build output rows
output = []

# 1. New article descriptions
for slug, desc in ARTICLE_DESCS.items():
    r = by_slug.get(slug)
    url = r['url'] if r else ''
    output.append({
        'type': 'article',
        'url': url,
        'slug': slug,
        'new_description': desc,
        'char_len': len(desc),
        'reason': 'generated',
        'gsc_clicks': int(r['gsc_clicks']) if r else 0,
    })

# 2. New tag descriptions
for tag_name, desc in TAG_DESCS.items():
    r = by_tag_name.get(tag_name)
    url = r['url'] if r else ''
    output.append({
        'type': 'tag',
        'url': url,
        'slug': tag_name,
        'new_description': desc,
        'char_len': len(desc),
        'reason': 'generated',
        'gsc_clicks': int(r['gsc_clicks']) if r else 0,
    })

# 3. Auto-truncated articles (>176 chars, not useless)
for r in rows:
    if r['url_type'] != 'article' or r['http_status'] != '200':
        continue
    desc = r['meta_description'].strip()
    if len(desc) <= 176:
        continue
    is_useless = bool(re.match(r'^(words by|created by|written by|by )\s+\w', desc.lower()))
    if is_useless:
        continue
    if r['slug'] in ARTICLE_DESCS:
        continue  # Already handled above
    truncated = smart_truncate(desc)
    output.append({
        'type': 'article',
        'url': r['url'],
        'slug': r['slug'],
        'new_description': truncated,
        'char_len': len(truncated),
        'reason': 'auto-truncated',
        'gsc_clicks': int(r['gsc_clicks'] or 0),
    })

# Write output
with open('/tmp/wxr_test/descriptions-final.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['type','url','slug','new_description','char_len','reason','gsc_clicks'])
    writer.writeheader()
    for row in sorted(output, key=lambda x: -x['gsc_clicks']):
        writer.writerow(row)

# Validate lengths
too_short = [r for r in output if r['char_len'] < 100]
too_long  = [r for r in output if r['char_len'] > 160]
print(f"\nDescriptions written: {len(output)}")
print(f"  Generated (articles): {sum(1 for r in output if r['type']=='article' and r['reason']=='generated')}")
print(f"  Generated (tags):     {sum(1 for r in output if r['type']=='tag')}")
print(f"  Auto-truncated:       {sum(1 for r in output if r['reason']=='auto-truncated')}")
print(f"\nQuality check:")
print(f"  < 100 chars (too short): {len(too_short)}")
print(f"  > 160 chars (too long):  {len(too_long)}")
if too_short:
    for r in too_short[:5]:
        print(f"    {r['char_len']:3d} chars  {r['slug'][:60]}")
if too_long:
    for r in too_long[:5]:
        print(f"    {r['char_len']:3d} chars  {r['slug'][:60]}")
print(f"\nWrote: /tmp/wxr_test/descriptions-final.csv")
