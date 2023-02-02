import sqlite3
import requests
import traceback
import sys
import json


def connect_to_database():
    global conn
    conn = sqlite3.connect('Houseit.db')

def disconnect_from_database():
   conn.close()


def invokeDataAPI(dataURL):
    global returnCode, returnMsg, conn, refreshFlag

    try:
        response = requests.get(dataURL)
        returnCode = "Success"
        returnMsg = response.text
    except requests.exceptions.HTTPError as errh:
        returnCode = "HttpError"
        returnMsg = errh
    except requests.exceptions.ConnectionError as errc:
        returnCode = "ConnectionError"
        returnMsg = errc
    except requests.exceptions.Timeout as errt:
        returnCode =  "TimeoutError"
        returnMsg = errt
    except requests.exceptions.RequestException as err:
        returnCode = "RequestError"
        returnMsg = err
    except Exception as excp:
        returnCode = "OtherException"
        returnMsg = excp


def parseAndInsertResaleData(jsonResponse):
    global resaleRecordsTotal, resaleRecordCnt, conn, cursor
    resaleResponeJson = json.loads(jsonResponse)
    prevTown = "";prevTownID = ""
    prevFlatType = "" ; prevFlatTypeID = ""
    prevFlatModel = ""; prevFlatModelID = ""
    prevStreetName = ""; prevStreetID = ""
    if ("total" in resaleResponeJson['result']):
        resaleRecordsTotal = resaleResponeJson['result']['total']
    else:
        resaleRecordsTotal = -1   # API has not give "total" so assume data is extracted in one API call
    nextURL =  resaleResponeJson['result']['_links']['next']
    resaleRows =[]
    for resaleProperty in resaleResponeJson['result']['records']:
        town = resaleProperty['town']
        if (prevTown == town) :
            townID = prevTownID
        else:
            townID = getTownID(town)
            prevTown = town
            prevTownID = townID

        flat_type = resaleProperty['flat_type']
        if (prevFlatType == flat_type):
            flatTypeID = prevFlatTypeID
        else:
            flatTypeID = getFlatTypeID(flat_type)
            prevFlatType = flat_type
            prevFlatTypeID = flatTypeID

        flat_model = resaleProperty['flat_model']
        if (prevFlatModel == flat_model):
            flatModelID = prevFlatModelID
        else:
            flatModelID = getFlatModelID(flat_model)
            prevFlatModel = flat_model
            prevFlatModelID = flatModelID

        floor_area_sqm = resaleProperty['floor_area_sqm']

        street_name = resaleProperty['street_name']
        if (prevStreetName == street_name) :
            streetID = prevStreetID
        else:
            streetID = getStreetID(street_name)
            prevStreetName = street_name
            prevStreetID = streetID


        resale_price = resaleProperty['resale_price']
        YYYYMM = resaleProperty['month']
        remaining_lease = resaleProperty['remaining_lease']
        lease_commence_date = resaleProperty['lease_commence_date']
        storey_range = resaleProperty['storey_range']
        block = resaleProperty['block']
        resalePropertyID = resaleProperty['_id']
        resaleRecordCnt = resaleRecordCnt + 1
        resaleRow = (resalePropertyID, YYYYMM, townID,flatTypeID,block,streetID,floor_area_sqm,flatModelID,lease_commence_date,remaining_lease,resale_price)     # group as tuple
        resaleRows.append(resaleRow)        # Add tuple to list
        #print(town+"*"+flat_type+"*"+flat_model+"*"+floor_area_sqm+"*"+street_name+"*"+resale_price+"*"+month+"*"+remaining_lease+"*"+lease_commence_date+"*"+storey_range+"*"+block)
    cursor.executemany("insert into MasterPropertyResaleData (resalePropertyID,YYYYMM,townID,flatTypeID ,block ,streetID ,floorAreaInSqm ,flatModelID ,leaseCommenceDate ,remainingLeaseYears ,resalePrice ) values(?,?,?,?,?,?,?,?,?,?,?)", resaleRows)
    conn.commit()
    print(str(resaleRecordCnt) + ' Processed..')
    return nextURL

def parseAndInsertRentalData(jsonResponse):
    global rentalRecordsTotal, rentalRecordCnt, conn, cursor
    rentalResponeJson = json.loads(jsonResponse)
    prevTown = "";prevTownID = ""
    prevFlatType = "" ; prevFlatTypeID = ""
    prevStreetName = ""; prevStreetID = ""
    if ("total" in rentalResponeJson['result']):
        rentalRecordsTotal = rentalResponeJson['result']['total']
    else:
        rentalRecordsTotal = -1   # API has not give "total" so assume data is extracted in one API call
    nextURL =  rentalResponeJson['result']['_links']['next']
    rentalRows =[]
    for rentalProperty in rentalResponeJson['result']['records']:
        town = rentalProperty['town']
        if (prevTown == town) :
            townID = prevTownID
        else:
            townID = getTownID(town)
            prevTown = town
            prevTownID = townID

        flat_type = rentalProperty['flat_type']
        if (prevFlatType == flat_type):
            flatTypeID = prevFlatTypeID
        else:
            flatTypeID = getFlatTypeID(flat_type)
            prevFlatType = flat_type
            prevFlatTypeID = flatTypeID

        street_name = rentalProperty['street_name']
        if (prevStreetName == street_name) :
            streetID = prevStreetID
        else:
            streetID = getStreetID(street_name)
            prevStreetName = street_name
            prevStreetID = streetID

        monthlyRent = rentalProperty['monthly_rent']
        YYYYMM = rentalProperty['rent_approval_date']
        block = rentalProperty['block']
        rentalPropertyID = rentalProperty['_id']
        rentalRecordCnt = rentalRecordCnt + 1
        rentalRow = (rentalPropertyID, YYYYMM, townID, block, streetID, flatTypeID, monthlyRent)     # group as tuple
        rentalRows.append(rentalRow)        # Add tuple to list
    cursor.executemany("insert into MasterPropertyrentalData (rentalPropertyID, YYYYMM, townID, block ,streetID ,flatTypeID, monthlyRent ) values(?,?,?,?,?,?,?)", rentalRows)
    conn.commit()
    print(str(rentalRecordCnt) + ' Processed..')
    return nextURL

def getTownID(town):
    global cursor
    dbTownID = ""
    cursor.execute("select townID from MasterTownData where townName = ?", (town,))
    townRow = cursor.fetchone()
    if townRow is None:
        cursor.execute("insert into MasterTownData (townName) values(?)", (town,))
        dbTownID= cursor.lastrowid
    else:
        dbTownID = townRow[0]
    return dbTownID


def getFlatTypeID(flat_type):
    global cursor
    dbflatTypeID = ""
    cursor.execute("select flatTypeID from MasterFlatTypes where flatType = ?", (flat_type,))
    townRow = cursor.fetchone()
    if townRow is None:
        cursor.execute("insert into MasterFlatTypes (flatType) values(?)", (flat_type,))
        dbflatTypeID = cursor.lastrowid
    else:
        dbflatTypeID = townRow[0]
    return dbflatTypeID

def getFlatModelID(flat_model):
    global cursor
    dbflatModel = ""
    cursor.execute("select flatModelID from MasterFlatModelData where flatModel = ?", (flat_model,))
    townRow = cursor.fetchone()
    if townRow is None:
        cursor.execute("insert into MasterFlatModelData (flatModel) values(?)", (flat_model,))
        dbflatModel = cursor.lastrowid
    else:
        dbflatModel = townRow[0]
    return dbflatModel

def getStreetID(street_name):
    global cursor
    # Cutoff Street number from street name.. so check last word if it is number
    splitStreet = street_name.split()
    streetNumber = splitStreet[-1]

    if (streetNumber.isnumeric()):
        street_name = " ".join(splitStreet[:-1])

    dbstreetID = ""
    cursor.execute("select streetID from MasterStreetData where streetName = ?", (street_name,))
    townRow = cursor.fetchone()
    if townRow is None:
        cursor.execute("insert into MasterStreetData (streetName) values(?)", (street_name,))
        dbstreetID = cursor.lastrowid
    else:
        dbstreetID = townRow[0]
    return dbstreetID

#main

def main():
    global refreshFlag, resaleRecordsTotal, resaleRecordCnt, cursor , rentalRecordsTotal, rentalRecordCnt
    # Connect to SQLLite database
    connect_to_database()

    cursor = conn.cursor()

    #Refresh MasterPropertyResaleData
    print("Populating Master Resale Database .. Type of Update .." + refreshFlag + "\n")
    MasterPropertyResaleDataCountQuery = "Select Count(*) from MasterPropertyResaleData"
    MasterPropertyResaleDataMaxID = "Select MAX(resalePropertyID) from MasterPropertyResaleData"
    MasterPropertyResaleDataDelete = "Delete from MasterPropertyResaleData"

    if (refreshFlag == "FULL"):
        cursor.execute(MasterPropertyResaleDataDelete)
        conn.commit()
        resaleRecordsOffset = 0
    else:                                                       # INCREMENTAL
        cursor.execute(MasterPropertyResaleDataCountQuery)
        resaleRecordCnt = cursor.fetchone()[0]

        if (resaleRecordCnt == 0) :
            resaleRecordsOffset = 0
        else:
            cursor.execute(MasterPropertyResaleDataMaxID)
            resaleRecordsTotal = cursor.fetchone()[0]
            resaleRecordsOffset = resaleRecordsTotal + 1

    # Popualate Master Resale Database
    dataHost ="https://data.gov.sg"
    dataUrl = "/api/action/datastore_search?offset="+str(resaleRecordsOffset)+"&"+"resource_id=f1765b54-a209-4718-8d38-a39237f502b3&limit=200000"

    moreDataExists = True

    while (moreDataExists):
        invokeDataAPI(dataHost+dataUrl)
        if returnCode == "Success":
            saveDataUrl = dataUrl
            dataUrl = parseAndInsertResaleData(returnMsg)  # next URL is parsed/extracted and returned by parseAndInsertResaleData function.
            if (saveDataUrl == dataUrl):    # if server gives back next as same as what we have already inquired then stop processing
                moreDataExists = False
        else:
            #Build json exception response and return. In this standalone program we will just print exception and exit
            print("Error refreshing Master Resale Data")
            print(">>> " + returnCode)
            print(">>> " + returnMsg)
            sys.exit("Retry after some time!!")

        if resaleRecordCnt >= resaleRecordsTotal :
            moreDataExists=False

    # Refresh MasterPropertyRentalData

    print("Populating Master Rental Database .. Type of Update .." + refreshFlag + "\n")
    MasterPropertyRentalDataCountQuery = "Select Count(*) from MasterPropertyRentalData"
    MasterPropertyRentalDataMaxID = "Select MAX(rentalPropertyID) from MasterPropertyRentalData"
    MasterPropertyRentalDataDelete = "Delete from MasterPropertyRentalData"

    if (refreshFlag == "FULL"):
        cursor.execute(MasterPropertyRentalDataDelete)
        conn.commit()
        rentalRecordsOffset = 0
    else:  # INCREMENTAL
        cursor.execute(MasterPropertyRentalDataCountQuery)
        rentalRecordCnt = cursor.fetchone()[0]

        if (rentalRecordCnt == 0):
            rentalRecordsOffset = 0
        else:
            cursor.execute(MasterPropertyRentalDataMaxID)
            rentalRecordsTotal = cursor.fetchone()[0]
            rentalRecordsOffset = rentalRecordsTotal + 1

    # Popualate Master Rental Database << to be implemented
    dataUrl = "/api/action/datastore_search?offset=" + str(
        rentalRecordsOffset) + "&" + "resource_id=9caa8451-79f3-4cd6-a6a7-9cecc6d59544&limit=200000"

    moreDataExists = True

    while (moreDataExists):
        invokeDataAPI(dataHost + dataUrl)
        if returnCode == "Success":
            saveDataUrl = dataUrl
            dataUrl = parseAndInsertRentalData(returnMsg)  # next URL is parsed/extracted and returned by parseAndInsertRentalData function.
            if (saveDataUrl == dataUrl):  # if server gives back next as same as what we have already inquired then stop processing
                moreDataExists = False
        else:
            # Build json exception response and return. In this standalone program we will just print exception and exit
            print("Error refreshing Master Rental Data")
            print(">>> " + returnCode)
            print(">>> " + returnMsg)
            sys.exit("Retry after some time!!")

        if rentalRecordCnt >= rentalRecordsTotal:
            moreDataExists = False


    #Disconnect from SQLLite database
    disconnect_from_database()

#invoke main
global returnCode , returnMsg , conn, refreshFlag
returnCode = "" ; returnMsg = ""; conn = "" ; cursor = None
resaleRecordsTotal = 0; resaleRecordCnt = 0
rentalRecordsTotal = 0; rentalRecordCnt = 0

# Provide on webpage 2 refresh options : "FULL" - Full Refresh which means delete master resale and rental data and populate fresh
#                                        "INCREMENTAL" - Incrementally refresh. Use max(resalePropertyID) or max(rentalPropertyID) and add 1 to set offset

refreshFlag = "FULL"

main()