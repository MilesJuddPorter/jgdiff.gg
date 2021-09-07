#!pip install cassiopeia

#%% Import Packages And Set API Key
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style('darkgrid')
import cassiopeia as cass

cass.set_riot_api_key("RGAPI-3bfbb6c6-0339-4d6d-bd20-36745d8138b1")
cass.set_default_region("NA")

#%% FUNC: start   --> Calls lots of functions (Runs the program)
def start():
  summoner_name = input("What is your Summoner Name (Make sure you are in a live game!)")
  summObject = getSummObject(summoner_name)
  currentMatchParticipants = (summObject.current_match).participants

  if summoner_name in list(p.summoner.name for p in currentMatchParticipants)[0:5]: #Get side so that we can show them the 5 champs from the other side to pick the jungler
    side = 'Blue'
  else:
    side='Red'

  enemyJunglerIndex = getEnemyJunglerIndex(currentMatchParticipants, side) #Gets a number that is the index of the other jungler in our summoner list

  enemyJunglerSummonerName = list(p.summoner.name for p in currentMatchParticipants)[enemyJunglerIndex]

  enemyjgSummObject = getSummObject(enemyJunglerSummonerName)

  enemyjgMatchHist = cass.get_match_history(summoner=enemyjgSummObject, end_index=30, queues=['RANKED_SOLO_5x5'])

  enemyjgSoloDuoRankedMatchHist = []
  for match in enemyjgMatchHist:
    if str(match.queue) == "Queue.ranked_solo_fives":
      enemyjgSoloDuoRankedMatchHist.append(match)
  
  enemyPlayTimeCountPlot = graphPlayTimes(enemyjgSoloDuoRankedMatchHist)

  enemyjgChampMastDF = createChampMastDF(enemyJunglerSummonerName)

  sns.barplot(x='Champion', y='Mastery Points', data=enemyjgChampMastDF[:10])
  plt.xticks(rotation=90)
  plt.show()
  plt.clf()

  for p in currentMatchParticipants:
    if p.summoner.name == enemyJunglerSummonerName:
      enemyjgChampID = p.champion.id

  matchHist = getMatchHist20(enemyJunglerSummonerName, enemyjgChampID)
  deathDF = getDeathInfoDF(matchHist, enemyJunglerSummonerName)
  plotDeathInfo(deathDF, '07:00')

  partList = getParticipantMatchHistory(enemyJunglerSummonerName, enemyjgChampID)
  df, redFirstKillDF, blueFirstKillDF = firstBackDF(partList)

  #Plot First Back Action Information (with df)
  timeKillFirstBackBarPlot(df)
  print("\nThis player gets a kill or assist "+ str(len(df[(df['Kills'] >0) | (df['Assists'] >0)]) / len(df) *100) + "% of the time before backing\n\n" )
  killAssistFirstBackStripPlot(df)

  #Plot First Back Kill Maps (with killDF)
  titleGraph1 = "Enemy JG First KorA When Red Side"
  titleGraph2 = "Enemy JG First KorA When Blue Side"
  killInformationLeaguePlot(redFirstKillDF, titleGraph1)
  killInformationLeaguePlot(blueFirstKillDF, titleGraph2)
  
  skillsDF = skillLevelUpDF(partList)
  sns.scatterplot(x='ThreeTimes', y='FourTimes', data=skillsDF)
  
  
  
#%% FUNC: getSummObject   --> RETURNS summoner object

#Function to return a summoner object
def getSummObject(summName):
  return cass.Summoner(name=summName)

#%% FUNC: getEnemyJunglerIndex   --> RETURNS index value


#Lets the user pick the index of the enemy jungler
def getEnemyJunglerIndex(matchParticipants, side):
  if side == "Blue":
    summList = list(p.summoner.name for p in matchParticipants)[5:10]
    var = 1
  else:
    summList = list(p.summoner.name for p in matchParticipants)[0:5]
    var = 0

  enemyjgIndex = input("Which number (1-5) corresponds with the enemy jungler? \n1 - " + summList[0] + "\n2 - " + summList[1] + "\n3 - " + summList[2] + "\n4 - " + summList[3] + "\n5 - " + summList[4] +"\n\n")
  return (int(enemyjgIndex) + (5*var) - 1)

#%% FUNC: createChampMastDF   --> RETURNS ChampMastery DataFrame


#FUNCTION TO CREATE A CHAMPION MASTERY DATA FRAME FOR SPECIFIC PLAYER (Champion - Mastery Points - Last Played)
def createChampMastDF(summonerName):
  champMast = cass.Summoner(name=summonerName).champion_masteries
  champMastDF = pd.DataFrame(columns=['Champion', 'Mastery Points', 'Last Played'])
  champs = []
  mastPoints = []
  lastPlayed = []
  for champ in champMast:
    if champ.points > 0: #If you don't have this '.last_played' creates an error because you have never played the champ
      champs.append(champ.champion.name)
      mastPoints.append(champ.points)
      lastPlayed.append((champ.last_played).format('YYYY-MM-DD')) #.last_played creates an arrow.arrow.Arrow object so I did some googling and you need the .format to get it how we want it

  champMastDF['Champion'], champMastDF['Mastery Points'], champMastDF['Last Played'] = champs, mastPoints, lastPlayed
  return champMastDF

#%% FUNC: graphPlayTimes(matchHistory)   --> GRAPH

def graphPlayTimes(matchHistory):
  dates = pd.DataFrame(columns=['Date', 'Yes'])
  datee = []
  yes = []
  for match in matchHistory:
    datee.append(match.creation.format('YYYY-MM-DD'))
    yes.append(1)
  
  dates['Date'] = datee
  dates['Yes'] = yes
  countplot = sns.countplot(x='Date', data=dates)
  plt.xticks(rotation=45)
  plt.show()
  plt.clf()
  return countplot

#%% FUNC: getDeathInfoDF(matchHistory, summonerName)   --> RETURNS dataframe with death info to append to larger DF

def getDeathInfoDF(matchHistory, summonerName):
  fullDeathDF = pd.DataFrame(columns=['Timestamp', 'x_loc', 'y_loc', 'KillerLane'])
  for match in matchHistory: #Iterate through match history
    matchParticipants = match.participants #Create match participant list for that game

    for p in matchParticipants: #Iterate through participants
      if p.summoner.name == summonerName:
        myPart = p #Select the participant with the right name
    
    myTimeline = myPart.timeline #Now I have my timeline from the specific match

    deathsInMatchDF = getDeathDFfromMatch(myTimeline, matchParticipants, matchHistory)
    fullDeathDF = pd.concat([fullDeathDF, deathsInMatchDF])

  return fullDeathDF

#%% FUNC: getDeathDFfromMatch(timeline, participantList, matchHistory)   --> RETURNS dataframe with death info

def getDeathDFfromMatch(timeline, participantList, matchHistory):

 #Deaths DataFrame ('Timestamp' 'x_loc', 'y_loc')
  champDeathDF = pd.DataFrame(columns=['Timestamp', 'x_loc', 'y_loc', 'KillerLane'])
  timestamp, x, y, killer = [], [], [], []
  champDeaths = timeline.champion_deaths

  for death in champDeaths:
    timestamp.append(str(death.timestamp)[2:7])
    xLoc, yLoc = position_to_map_image_coords(death.position)
    x.append(xLoc)
    y.append(yLoc)
    killer.append(participantList[death.killer_id-1].lane)

  champDeathDF['Timestamp'], champDeathDF['x_loc'], champDeathDF['y_loc'], champDeathDF['KillerLane'] = timestamp, x, y, killer
  

  return champDeathDF

#%% FUNC: position_to_map_image_coords(position)   --> Converts a position object to x/y fitted positions

def position_to_map_image_coords(position):
  rx0, ry0, rx1, ry1 = 0, 0, 14820, 14881
  imx0, imy0, imx1, imy1 = 0, 0, 512, 512
  x, y = position.x, position.y
  x -= rx0
  x /= (rx1 - rx0) #(14820)
  x *= (imx1 - imx0) #(512)
  y -= ry0
  y /= (ry1 - ry0)
  y *= (imy1 - imy0)
  y = imy1 - y
  return x, y

#%% FUNC: getMatchHist20(summName, champID)   --> RETURNS match historty object

def getMatchHist20(summName, champID):
  mh = cass.get_match_history(summoner=cass.Summoner(name=summName), champions = [champID], queues=['RANKED_SOLO_5x5'], end_index=40)
  return mh
#%% FUNC: plotDeathInfo(deathDF, time)   --> CREATES A GRAPH


def plotDeathInfo(deathDF, time): #Where -  time = string (eg: '07:00') AND hue = column name from dataframe
  match = cass.get_match(id=4007884684)
  sns.set_style('white')
  #GRAPH 1: By Time
  size = 8
  plt.figure(figsize=(size, size))
  plt.imshow(match.map.image.image.rotate(0))
  sns.scatterplot(x='x_loc', y='y_loc', data=deathDF, palette='Blues', hue='Timestamp', s=60, legend=None)
  plt.title("Deaths By Time Throughout The Game")
  plt.xlabel('')
  plt.ylabel('')
  plt.show()
  plt.clf()

  #GRAPH 2: By Lane
  size = 8
  plt.figure(figsize=(size, size))
  plt.imshow(match.map.image.image.rotate(0))
  sns.scatterplot(x='x_loc', y='y_loc', data=deathDF[deathDF['Timestamp'] < time], palette='tab10', hue='KillerLane', s=60)
  plt.title("Deaths By Lane In The First " + time)
  plt.xlabel('')
  plt.ylabel('')
  plt.show()
  sns.set_style('darkgrid')
  
#%% FUNC: getParticipantMatchHistory(summName, champID)   --> RETURNS participant list (Alt. match list)

  #Create a list of 'Participant Objects' of that player rather than match history
def getParticipantMatchHistory(summName, champID):
  summMH = getMatchHist20(summName, champID)
  myPartList = []
  for match in summMH:
    matchParts = match.participants
    for p in matchParts:
      if p.summoner.name == summName:
        myPartList.append(p)
  return myPartList

#%% FUNC: firstBackDF(participantList)   --> RETURNS firstBackDF, redKillDF, blueKillDF

def firstBackDF(participantList):
  firstBackDF = pd.DataFrame(columns=['First Back Time', 'Level', 'Kills', 'Assists', 'Wards Placed', 'Starting Item', 'Ward Trick'])
  firstKillInformationRedSideDF = pd.DataFrame(columns=['Timestamp', 'x_loc', 'y_loc', 'Kill/Assist'])
  firstKillInformationBlueSideDF = pd.DataFrame(columns=['Timestamp', 'x_loc', 'y_loc', 'Kill/Assist'])
  fbTimeList = []
  levelList = []
  killsList = []
  assistsList = []
  wardsPlacedList = []
  startingItemList = []
  wardTrickList = []

  for p in participantList:
    if str(p.side) == "Side.blue":
        side = "Blue"
    elif str(p.side) == "Side.red":
        side = "Red"
    else:
        print("Well I fucked up...")
    userID = p.id
    timeline = p.timeline
    fbEventList = getFirstBackEventObjects(timeline)
    if str(type(fbEventList)).find('list') == -1:
      print('Just Squashed A Bug #DemonMode')
      continue
    fbTime = round((fbEventList[-1].timestamp.seconds)/60, 2)
    level = 0
    wardsPlaced = 0
    kills = 0
    assists = 0
    wardTrick = 0
    skillLevelUpEventList = []
    firstKillRedEventList = []
    firstKillBlueEventList = []
    startingItem = "Unknown"
    
    
    for event in fbEventList[:-1]:
      
      if event.type == "SKILL_LEVEL_UP":
        level += 1
      elif event.type == "WARD_PLACED":
        wardsPlaced += 1
        if event.timestamp.seconds < 90:
          startOfWardTrickBool = True          
      elif event.type == "CHAMPION_KILL":
        if kills == 0 and assists == 0: #If it's the first kill in this new series append to firstKill
            if side == "Red":
                firstKillRedEventList.append(event)
            elif side == "Blue":
                firstKillBlueEventList.append(event)
        if event.killer_id == userID:
          kills += 1
        elif event.killer_id != userID:
          assists += 1
      
      if event.type == "ITEM_PURCHASED":
        if event.item_id == 1039:
          startingItem = "Hailblade"
        elif event.item_id == 1035:
          startingItem = "Emberknife"
        elif event.item_id == 3341 and startOfWardTrickBool == True:
          wardTrick = 1
    
    fbTimeList.append(fbTime), levelList.append(level), killsList.append(kills), assistsList.append(assists), wardsPlacedList.append(wardsPlaced), startingItemList.append(startingItem), wardTrickList.append(wardTrick)

    #Do something with kill event list
    redFirstKillGameInformationDF = getKillDFWithChampKillEventList(firstKillRedEventList, userID)
    blueFirstKillGameInformationDF = getKillDFWithChampKillEventList(firstKillBlueEventList, userID)
    
    firstKillInformationRedSideDF = pd.concat([firstKillInformationRedSideDF, redFirstKillGameInformationDF])
    firstKillInformationBlueSideDF = pd.concat([firstKillInformationBlueSideDF, blueFirstKillGameInformationDF])
  
  firstBackDF['First Back Time'], firstBackDF['Level'], firstBackDF['Kills'], firstBackDF['Assists'], firstBackDF['Wards Placed'], firstBackDF['Starting Item'], firstBackDF['Ward Trick'] = fbTimeList, levelList, killsList, assistsList, wardsPlacedList, startingItemList, wardTrickList

  return firstBackDF, firstKillInformationRedSideDF, firstKillInformationBlueSideDF

#%% FUNC: getKillDFWithChampKillEventList(champKillEventList, userID)   --> RETURNS DF about Kills

def getKillDFWithChampKillEventList(champKillEventList, userID):
  killInformationDF = pd.DataFrame(columns=['Timestamp', 'x_loc', 'y_loc', 'Kill/Assist'])
  timestamp, x, y, KorA = [], [], [], []

  for kill in champKillEventList:
    timestamp.append(str(kill.timestamp)[2:7])
    xLoc, yLoc = position_to_map_image_coords(kill.position)
    x.append(xLoc)
    y.append(yLoc)
    if kill.killer_id == userID:
      KorA.append('K')
    else:
      KorA.append('A')

  killInformationDF['Timestamp'], killInformationDF['x_loc'], killInformationDF['y_loc'], killInformationDF['Kill/Assist'] = timestamp, x, y, KorA
  return killInformationDF

#%% FUNC: getFirstBackEventObjects(timeline)   --> RETURNS event list


def getFirstBackEventObjects(timeline):
  eventList = []
  for event in timeline.events:
    eventList.append(event)
    if event.type == "ITEM_PURCHASED" and str(event.timestamp)[2:7] > '02:00':
      return eventList
      break
  
#%% FUNC: timeKillFirstBackBarPlot(df)   --> GRAPH

#PLOT FIRST BACK TIME/KILL INFO
def timeKillFirstBackBarPlot(df):
  plt.hist([  df[(df['Kills'] == 0) & (df['Assists'] == 0)]['First Back Time'], df[ (df['Kills'] > 0) | (df['Assists'] > 0)]['First Back Time'] ], stacked=True, color=['r', 'b'], alpha=0.5)
  plt.legend(['No Kill/Assist', 'Got A Kill/Assist'])
  plt.axvline(3.25, 0, 1, color='green') #WE LOVE SCUTTLE
  plt.text(3.2, -1, 'Scuttle', rotation=90, color='Green')
  plt.title("First Back By Time and Kill")
  plt.xlabel('Minute')
  plt.ylabel('Frequency')
  plt.show()
  
#%% FUNC: killAssistFirstBackStripPlot(df)   --> GRAPH

#KILLS/ASSISTS STRIP PLOT
def killAssistFirstBackStripPlot(df):
  sns.stripplot(x='Kills', y='Assists', data=df, hue='Starting Item', jitter=True)
  plt.title('Frequency of Kill/Assist Combinations (Before First Back)')
  plt.show()
  
#%% FUNC: killInformationLeaguePlot(df, title)  --> GRAPH
def killInformationLeaguePlot(df, setTitle):
  sns.set_style('white')
  match = cass.get_match(id=4007884684)
  #GRAPH 1: By Time
  size = 8
  plt.figure(figsize=(size, size))
  plt.imshow(match.map.image.image.rotate(0))
  sns.scatterplot(x='x_loc', y='y_loc', data=df, palette='tab10', hue='Kill/Assist', s=60)
  plt.title(setTitle)
  plt.xlabel('')
  plt.ylabel('')
  plt.show()
  sns.set_style('darkgrid')
  

#%% FUNC: skillLevelUpDF(participantList)


def skillLevelUpDF(participantList):
    skillDF = pd.DataFrame(columns=['TwoSkill', 'TwoTimes', 'ThreeSkill', 'ThreeTimes', 'FourSkill', 'FourTimes',])
    

    twoSkills = []
    twoTime = []
    
    threeSkills = []
    threeTime = []
    
    fourSkills = []
    fourTime = []
    
    killsWhileThree = []
    killsWhileFour = []
    
    for p in participantList:
        level = 0
        for event in p.timeline.events:
            if event.type == "CHAMPION_KILL":
                if level == 3:
                    killsWhileThree.append(event)
                elif level == 4:
                    killsWhileFour.append(event)
            
            if event.type == "SKILL_LEVEL_UP":
                level += 1
                if level == 1:
                    print('LVL1')
                elif level == 2:
                    twoSkills.append(event.skill)
                    levelTwoSecondsTime = event.timestamp.seconds
                    twoTime.append(levelTwoSecondsTime)
                elif level == 3:
                    threeSkills.append(event.skill)
                    levelThreeSecondsTime = event.timestamp.seconds
                    threeTime.append(levelThreeSecondsTime)
                elif level == 4:
                    fourSkills.append(event.skill)
                    levelFourSecondsTime =  event.timestamp.seconds
                    fourTime.append(levelFourSecondsTime)
    
    skillDF['TwoSkill'], skillDF['TwoTimes'], skillDF['ThreeSkill'], skillDF['ThreeTimes'], skillDF['FourSkill'], skillDF['FourTimes'] = twoSkills, twoTime, threeSkills, threeTime, fourSkills, fourTime
    
    return skillDF

#%%

#inspPartList = getParticipantMatchHistory('InspyreLoL', 28)

#inspEveSkillLevelUpDF = skillLevelUpDF(inspPartList)
#inspEveSkillz = inspEveSkillLevelUpDF[4:8]
#buffOnBlueSide = ["B", "B", "B", "R"]
#sns.scatterplot(data=inspEveSkillz,x='TwoTimes', y='FourTimes', hue=buffOnBlueSide)
#plt.hist(x= inspEveSkillLevelUpDF['FourTimes'], bins=20)

#startingPosSideAndTopOrBot(["Red":"Bot":"Full Clear"], ["Red":"Bot":"MouseDiedAfterRed"], ["Red":"Bot":"Ganked After Raps"],
                           #["Red":"Bot":"Full Clear"], ["Blue":"Top":"Full Clear"], ["Blue":"Top":"Full Clear"], ["Blue":"Bot":"Full Clear"]
                           #["Blue":"Top":"Gank after Red"])



#%%
testmh = cass.get_match_history(summoner=cass.Summoner(name='InspyreLoL'), champions = [28], queues=['RANKED_SOLO_5x5'], end_index=30)