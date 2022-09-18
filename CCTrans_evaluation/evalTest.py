import json
import copy
import pandas as pd
from pandas import json_normalize


# [SC] not a tree but DAG; the same input can be used at multiple levels
# [SC] assumptions:
# - "after" contains always only one element
# - if "type" has multiple values then always use the first one
# - the order of elements in cctrans matters; the first element is the first transformation; the last element is the final transformation
def evaluate(jsonFilename):
    with open(f"{jsonFilename}.txt", encoding='utf-8') as f:
        questions = json.load(f)

        for q in questions:
            # [SC] dictionary of all types; id is type id; created for an ease of access
            allTypes = {}
            for type in q["types"]:
                type["ccShort"] = f"{type['type'][0]}({type['keyword']})"
                allTypes[type["id"]] = type

            # [SC] add dictionary records for IDs (etc "5_u") not listed in "types"
            for trans in q["cctrans"]:
                for aTypeId in trans["after"]:
                    if aTypeId not in allTypes.keys():
                        orgTypeId = aTypeId.split("_")[0]
                        allTypes[aTypeId] = copy.deepcopy(allTypes[orgTypeId])
                        allTypes[aTypeId]["id"] = aTypeId

            # [SC] serialize each after/before transformation
            for trans in q["cctrans"]:
                str = "("

                # [SC] serialize befores
                for bIndex in range(len(trans["before"])):
                    bTypeId = trans["before"][bIndex]

                    if "ccLong" in allTypes[bTypeId].keys():
                        str += allTypes[bTypeId]["ccLong"]
                    else:
                        str += allTypes[bTypeId]["ccShort"]

                    if bIndex < len(trans["before"]) - 1:
                        str += ", "

                # [SC] serialize after
                aTypeId = trans['after'][0]
                str += f" -> {allTypes[aTypeId]['ccShort']})"
                allTypes[aTypeId]['ccLong'] = str

            # [SC] get the entire transformation
            finalId = q["cctrans"][len(q["cctrans"])-1]["after"][0]
            # [SC] store the entire transformation in the json
            q["ccAuto"] = allTypes[finalId]["ccLong"]

            # [SC] remove all white spaces and change to lower case before comparing two strings
            ccAuto = q["ccAuto"].replace(" ", "").lower()
            ccHuman = q["cc"].replace(" ", "").lower()

            # [SC] compare manual and auto CCs as strings
            print(f"Questions: {q['q']}")
            print(f"Manual cc: {ccHuman}")
            print(f"Auto-generated cc: {ccAuto}")
            if ccAuto == ccHuman:
                print("SAME")
                q["eval"] = 1
            else:
                print("DIFFERENT")
                q["eval"] = 0
            print("")

        with open(f'{jsonFilename}_evaluated.txt', 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=4)


def compareBasic(mq, aq):
    cdict = {"cctrans": 1,
                "extent": 0, "extentMatchCount": 0, "mExtent": 0, "aExtent": 0,
                "temporalEx": 0, "temMatchCount": 0, "mTem": 0, "aTem": 0,
                "typesStrict": 0, "typeMatchCount": 0, "mTypes": "NA", "aTypes": "NA",  #"typesLib": 0, "excessTypes": "NA",
                "transStrict": 0, "transMatchCount": 0, "mTrans": "NA", "aTrans": "NA",  #"excessTrans": "NA",
                "question": 0, "q": mq["question"]}


    # print("=====================================================")
    # print(mq["question"])

    ############################################################
    ## [SC] check manual cctrans
    mTrans = mq["cctrans"]

    if "extent" in mTrans:
        cdict["mExtent"] = len(mTrans["extent"])

    if "temporalEx" in mTrans:
        cdict["mTem"] = len(mTrans["temporalEx"])

    if "types" not in mTrans or len(mTrans["types"]) == 0:
        print(f"'{mq['question']}' does not contain types in manual json")
        return cdict
    else:
        cdict["mTypes"] = len(mTrans["types"])

    if "transformation" not in mTrans or len(mTrans["transformation"]) == 0:
        print(f"'{mq['question']}' does not contain transformation in manual json")
        return cdict
    else:
        cdict["mTrans"] = len(mTrans["transformation"])

    ############################################################
    ## [SC] check presense of cctrans in auto json

    if "cctrans" not in aq:
        cdict["cctrans"] = 0
        return cdict
    else:
        aTrans = aq["cctrans"]

    ############################################################
    ## [SC] compare extent

    # if "extent" in mTrans and "extent" in aTrans:
    #     if "".join(mTrans["extent"]) == "".join(aTrans["extent"]):
    #         cdict['extent'] = "Exact"
    #     elif set(mTrans["extent"]) & set(aTrans["extent"]):
    #         cdict['extent'] = "Partial"
    # elif "extent" not in mTrans and "extent" not in aTrans:
    #     cdict['extent'] = "Exact"

    extentMatchCount = 0
    if "extent" in mTrans:
        if "extent" in aTrans:
            aExtents = copy.deepcopy(aTrans["extent"])
            cdict["aExtent"] = len(aTrans["extent"])
            for mExtent in mTrans["extent"]:
                for aextent in aExtents:
                    if aextent == mExtent:
                        extentMatchCount += 1
            cdict["extent"] = round(extentMatchCount / len(mTrans["extent"]), 2)
            cdict["extentMatchCount"] = extentMatchCount
        else:
            cdict["aExtent"] = 0
    else:
        if "extent" not in aTrans:
            cdict["extent"] = 1


    ############################################################
    ## [SC] compare temporal extent

    # if "temporalEx" in mTrans and "temporalEx" in aTrans:
    #     if "".join(mTrans["temporalEx"]) == "".join(aTrans["temporalEx"]):
    #         cdict['temporalEx'] = "1"
    #     elif set(mTrans["temporalEx"]) & set(aTrans["temporalEx"]):
    #         cdict['temporalEx'] = "Partial"
    # elif "temporalEx" not in mTrans and "temporalEx" not in aTrans:
    #     cdict['temporalEx'] = "Exact"

    temMatchCount = 0
    if "temporalEx" in mTrans:
        if "temporalEx" in aTrans:
            aTems = copy.deepcopy(aTrans["temporalEx"])
            cdict["aTem"] = len(aTrans["temporalEx"])
            for mTem in mTrans["temporalEx"]:
                for aTem in aTems:
                    if aTem == mTem:
                        temMatchCount += 1
            cdict["temporalEx"] = round(temMatchCount / len(mTrans["temporalEx"]), 2)
            cdict["temMatchCount"] = temMatchCount
        else:
            cdict["aTem"] = 0
    else:
        if "temporalEx" not in aTrans:
            cdict["temporalEx"] = 1

    ############################################################
    ## [SC] compare types

    if "types" not in aTrans or len(aTrans["types"]) == 0:
        print(f"'{aq['question']}' does not contain types in auto json")
        return cdict
    cdict["aTypes"] = len(aTrans["types"])

    # [SC] strict comparison including keywords
    aTypes = copy.deepcopy(aTrans["types"])
    typeMatchCount = 0
    for mType in mTrans["types"]:
        # print(mType)

        for aType in aTypes:
            if ("matched" not in aType and
                mType["type"][0] == aType["type"][0] and
                mType["keyword"] == aType["keyword"]):
                aType["matched"] = True
                typeMatchCount += 1

                # print(aType)

                break
        # print("")
    cdict["typesStrict"] = round(typeMatchCount / len(mTrans["types"]), 2)
    cdict["typeMatchCount"] = typeMatchCount


    # [SC] liberal comparison excluding keywords
    # aTypes = copy.deepcopy(aTrans["types"])
    # matchCount = 0
    # for mType in mTrans["types"]:
    #     for aType in aTypes:
    #         if ("matched" not in aType and
    #             mType["type"][0] == aType["type"][0]):
    #             aType["matched"] = True
    #             matchCount += 1
    #             break
    # cdict["typesLib"] = round(matchCount / len(mTrans["types"]), 2)
    #
    # cdict["excessTypes"] = len(aTrans["types"]) - len(mTrans["types"])

    ############################################################
    ## [SC] compare transformations based on strict type comparison

    aTypes = copy.deepcopy(aTrans["types"])
    aTransform = copy.deepcopy(aTrans["transformation"])

    # [SC] assign temp IDs to types
    for aType in aTypes:
        aType["id"] = f"t{aType['id']}"   # [X] id = t0 / t1..
        aType["matched"] = False
    # [SC] assign temp IDs to transformation
    for chain in aTransform:
        for index in range(len(chain["before"])):
            chain["before"][index] = f"t{chain['before'][index]}"
        for index in range(len(chain["after"])):
            chain["after"][index] = f"t{chain['after'][index]}"
        chain["matched"] = False

    # [SC] ensure that matching manual and auto types have the same IDs
    for mType in mTrans["types"]:
        for aType in aTypes:
            if ((not aType["matched"]) and
                    mType["type"][0] == aType["type"][0] and
                    mType["keyword"] == aType["keyword"]):
                aType["matched"] = True

                # [SC] assigning manual type id to auto transformation id
                for chain in aTransform:
                    for index in range(len(chain["before"])):
                        # [SC] split is used since id can be something like 't2_u_u'
                        beforeId = chain["before"][index].split("_")
                        if beforeId[0] == aType["id"]:
                            if len(beforeId) == 1:
                                chain["before"][index] = mType["id"]
                            else:
                                chain["before"][index] = f"{mType['id']}_" + "_".join(beforeId[1:len(beforeId)])
                    for index in range(len(chain["after"])):
                        afterId = chain["after"][index].split("_")
                        if afterId[0] == aType["id"]:
                            if len(afterId) == 1:
                                chain["after"][index] = mType["id"]
                            else:
                                chain["after"][index] = f"{mType['id']}_" + "_".join(afterId[1:len(afterId)])

                    # for index in range(len(chain["before"])):
                    #     # [SC] split is used since id can be something like 't2_u_u'
                    #     if chain["before"][index].split("_")[0] == aType["id"]:
                    #         chain["before"][index] = mType["id"]
                    # for index in range(len(chain["after"])):
                    #     if chain["after"][index].split("_")[0] == aType["id"]:
                    #         chain["after"][index] = mType["id"]

                # [SC] assing manual type id to auto type id
                aType["id"] = mType["id"]

                break

    transMatchCount = 0
    for mChain in mTrans["transformation"]:
        mChain["before"].sort()
        mChain["after"].sort()

        mBefore = "".join(mChain["before"])
        mAfter = "".join(mChain["after"])

        for aChain in aTransform:
            aChain["before"].sort()
            aChain["after"].sort()

            aBefore = "".join(aChain["before"])
            aAfter = "".join(aChain["after"])

            if ((not aChain["matched"]) and
                mBefore == aBefore and
                mAfter == aAfter):
                aChain["matched"] = True
                transMatchCount += 1
                break

    # print(mTrans["types"])
    # print(aTypes)
    # print("")
    # print(mTrans["transformation"])
    # print(aTransform)


    cdict["transStrict"] = round(transMatchCount / len(mTrans["transformation"]), 2)
    cdict["transMatchCount"] = transMatchCount
    cdict["aTrans"] = len(aTrans["transformation"])
    # cdict["excessTrans"] = len(aTrans["transformation"]) - len(mTrans["transformation"])

    if cdict["extent"] == 1 and cdict["temporalEx"] == 1 and cdict["typesStrict"] == 1 and cdict["transStrict"] == 1:
        cdict["question"] = 1

    return cdict

# Which airports are within 50 mile of Crook, Deschutes and Jefferson county
# What areas are within 60 minutes of airports in Crook, Deschutes, and Jefferson county
# Where are the clusters of fatal car accidents with at least three incidents that are within a 300-meter area in the United State
# What are the housing districts outside 15 minutes driving time from Covid testing sites in Connecticut
# What is the number of traffic accidents clustered together in Pasadena, California
# What is the difference between breast cancer mortality rates of black women and white women for each county in the US
# [SC][NOTE] when comparing one type to another, only the first element in the list is considered
# [SC][NOTE] extent and temporalEx should always be present even if with empty list
# [SC][NOTE] manual annotation for What are the housing districts outside 15 minutes driving time from Covid testing sites in Connecticut needs to be corrected
def compare(manualFilename, autoFilename, saveFilename):
    with open(f"{manualFilename}", encoding='utf-8') as mFile:
        manJson = json.load(mFile)

        with open(f"{autoFilename}", encoding='utf-8') as aFile:
            autoJson = json.load(aFile)

            resultsJson = []

            for mq in manJson:
                removeElem = False
                for aq in autoJson:
                    if mq["question"] == aq["question"]:
                        removeElem = aq
                        break
                if removeElem:
                    resultsJson.append(compareBasic(mq, aq))
                    autoJson.remove(removeElem)
                else:
                    print(f"{mq['question']} is not found in auto annotation")

            resultsDF = json_normalize(resultsJson)
            resultsDF.to_csv(f'{saveFilename}.csv', index=False)


if __name__ == '__main__':
    # evaluate("testQuestionMod")

    compare("Results_test_Manual.json", "Results_test_Auto.json", "comparisonResults")