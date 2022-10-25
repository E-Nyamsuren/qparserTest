#[SC][TODO] is it necessary to consider cct types in generating additional rules
#[SC][TODO] remove the valid key from final qJson
#[SC][TODO] revise the query structure to include keywords

import json
import re


class T:
    # [SC] static variables
    hierarchyK = "hierachy"
    superK = "super"
    subK = "sub"

    termsK = "terms"
    conceptK = "concept"
    cctK = "cct"  # [SC] used in more than one Json

    validK = "valid"

    questionK = "question"
    cctransK = "cctrans"
    typesK = "types"
    idK = "id"
    typeK = "type"
    measureK = "measureLevel"
    extentK = "extent"
    transformK = "transformations"
    beforeK = "before" # [SC] used in more than one Json
    afterK = "after" # [SC] used in more than one Json
    keyK = "key"

    inputTypeK = "inputType"
    lhsK = "lhs"
    rhsK = "rhs"
    descrK = "description"
    afterIdK = "afterId"

    queryK = "query"
    queryExK = "queryEx"


class Logger:
    # [SC] static variables
    printConsole = True

    ERROR_TYPE = "ERROR"
    WARNING_TYPE = "WARNING"
    INFO_TYPE = "INFO"

    # [SC] Custom static printing method.
    # @param    string  type    Message type (ERROR, WARNING, INFO, etc).
    # @param    string  method  Name of the method that call this method.
    # @param    string  msg     Message to be printed.
    # @return   void
    @staticmethod
    def cPrint(type, method, msg):
        if Logger.printConsole:
            print(f"{type}: {msg} in method '{method}'")



class HConcept:
    def __init__(self, conceptStrP, cctStrP=None):
        # [SC] a unique string identfier of this node # [TODO] getter/setter
        self.conceptStr = conceptStrP
        # [SC] list of direct parent objects, instances of HConcept class
        self.parents = []
        # [SC] list of direct child objects, instances of HConcept class
        self.children = []
        # [SC] cct expression of this concept # [TODO] getter/setter
        self.cctStr = cctStrP

    # [SC] getter method for 'conceptStr' field
    # @return   string  Value of conceptStr
    # def getConceptStr(self):
    #     return self.conceptStr

    # [SC] setter method for 'cctStr' field
    # @param    string  cctStrP     New value for cctStrP
    # @return   void
    # def setCCT(self, cctStrP):
    #     self.cctStr = cctStrP

    # [SC] getter method for 'cctStr' field
    # @return   string  Value of cctStr
    # def getCCT(self):
    #     return self.cctStr

    # [SC] returns true if there is a parent with given string identifier
    # @param    string  conceptStrP     identifier of the parent concept
    # @return   boolean                 True if a matching parent is found, False otherwise
    def hasParent(self, conceptStrP):
        if self.hasDirectParent(conceptStrP):
            return True
        else:
            for parent in self.parents:
                if parent.hasParent(conceptStrP):
                    return True
        return False

    # [SC] returns true if there is a direct parent with given string identifier
    # @param    string  conceptStrP     identifier of the parent concept
    # @return   boolean                 True if a matching direct parent is found, False otherwise
    def hasDirectParent(self, conceptStrP):
        for parent in self.parents:
            if parent.conceptStr.lower() == conceptStrP.lower():
                return True
        return False

    # [SC] returns true if there is a child with given string identifier
    # @param    string  conceptStrP     identifier of the child concept
    # @return   boolean                 True if a matching child is found, False otherwise
    def hasChild(self, conceptStrP):
        if self.hasDirectChild(conceptStrP):
            return True
        else:
            for child in self.children:
                if child.hasChild(conceptStrP):
                    return True
        return False

    # [SC] returns true if there is a direct child with given string identifier
    # @param    string  conceptStrP     identifier of the child concept
    # @return   boolean                 True if a matching direct child is found, False otherwise
    def hasDirectChild(self, conceptStrP):
        for child in self.children:
            if child.conceptStr.lower() == conceptStrP.lower():
                return True
        return False

    # [SC] Returns a list of string identifiers of all parents of this node
    # @return   list    A list with string identifiers
    def getAllParentsStr(self):
        parentsStr = []
        for parent in self.parents:
            parentsStr.append(parent.conceptStr)
            parentsStr.extend(parent.getAllParentsStr())
        return list(set(parentsStr))

    # [SC] Returns a list of string identifiers of all children of this node
    # @return   list    A list with string identifiers
    def getAllChildrenStr(self):
        childrenStr = []
        for child in self.children:
            childrenStr.append(child.conceptStr)
            childrenStr.extend(child.getAllChildrenStr())
        return list(set(childrenStr))


class TypesToQueryConverter:
    # [SC][TODO]
    def isRulesLoaded(self):
        if not convRules:
            return False
        return True


    # [SC][TODO]
    def isConsistentRules(self):
        # [TODO]
        return True


    # [SC][TODO] cardinality of json objects with the same key is not considered (e.g., "type":"object","type":"field")
    # [SC] Sets qJson['valid'] to "T" if a question annotation has a valid structure and values, and to "F" otherwise.
    # @param    dictionary  qJson   A JSON object of the question annotation.
    # @return   void
    def isValidQJson(self, qJson):
        methodName = "TypesToQueryConverter.isValidQJson"
        typeIds = []
        questionStr = "?"
        qJson[T.validK] = "T"

        if T.questionK not in qJson:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"'{T.questionK}' not found in '{qJson}'.")
            qJson[T.validK] = "F"
        else:
            questionStr = qJson[T.questionK]

        if T.cctransK not in qJson:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"'{T.cctransK}' not found in '{questionStr}'.")
            qJson[T.validK] = "F"
            return

        if T.typesK not in qJson[T.cctransK]:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"'{T.typesK}' not found in '{questionStr}'.")
            qJson[T.validK] = "F"
            return
        else:
            typesList = qJson[T.cctransK][T.typesK]
            if not typesList:
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                            , f"'{T.typesK}' has empty value in '{questionStr}'.")
                qJson[T.validK] = "F"
            elif not isinstance(typesList, list):
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                            , f"'{T.typesK}' is not a list in '{questionStr}'.")
                qJson[T.validK] = "F"
            else:
                for typeObj in typesList:
                    typeId = "?"
                    # [SC] validate 'id' in type object
                    if T.idK not in typeObj:
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"'{T.idK}' is missing for type object in '{questionStr}'.")
                        qJson[T.validK] = "F"
                    elif not typeObj[T.idK]:
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"'{T.idK}' has empty value for type object in '{questionStr}'.")
                        qJson[T.validK] = "F"
                    elif not isinstance(typeObj[T.idK], str):
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"'{T.idK}' for a type object does not have a string value in '{questionStr}'.")
                        qJson[T.validK] = "F"
                    elif typeObj[T.idK] in typeIds:
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"Duplicate 'id={typeObj[T.idK]}' for type object is found in '{questionStr}'.")
                        qJson[T.validK] = "F"
                    else:
                        typeIds.append(typeObj[T.idK])
                        typeId = typeObj[T.idK]

                    # [SC] validate 'type' in type object
                    if T.typeK not in typeObj:
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"'{T.typeK}' is missing for type object with id '{typeId}' in '{questionStr}'.")
                        qJson[T.validK] = "F"
                    elif not isinstance(typeObj[T.typeK], str):
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"'{T.typeK}' is not a string for type object with id '{typeId}' in '{questionStr}'.")
                        qJson[T.validK] = "F"
                    elif typeObj[T.typeK] not in hConceptHierarchy:
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"Invalid 'type={typeObj[T.typeK]}' for type object with id '{typeId}' in '{questionStr}'.")
                        qJson[T.validK] = "F"

                    # [SC] validate 'measureLevel' in type object
                    if T.measureK in typeObj:
                        if not isinstance(typeObj[T.measureK], str):
                            Logger.cPrint(Logger.ERROR_TYPE, methodName
                                        , f"'{T.measureK}' is not a string for type object with id '{typeId}' in '{questionStr}'.")
                            qJson[T.validK] = "F"
                        elif typeObj[T.measureK] not in measureHierarchy:
                            Logger.cPrint(Logger.ERROR_TYPE, methodName
                                        , f"Invalid 'measureLevel={typeObj[T.measureK]}' for type object with id '{typeId}' in '{questionStr}'.")
                            qJson[T.validK] = "F"

                    # [SC][TODO] check cct against all possible expression
                    # if 'cct' in typeObj:

        # [SC] validate 'extent'
        if T.extentK not in qJson[T.cctransK]:
            Logger.cPrint(Logger.WARNING_TYPE, methodName
                        , f"'{T.extentK}' not found in '{questionStr}'.")
            # qJson[T.validK] = "F"
        else:
            extentObj = qJson[T.cctransK][T.extentK]
            if not isinstance(extentObj, list):
                Logger.cPrint(Logger.WARNING_TYPE, methodName
                            , f"'{T.extentK}' is not a list in '{questionStr}'.")
                # qJson[T.validK] = "F"
            elif len(extentObj) != 1:
                Logger.cPrint(Logger.WARNING_TYPE, methodName
                            , f"'{T.extentK}' should have exactly one value in '{questionStr}'.")
                # qJson[T.validK] = "F"
            elif extentObj[0] not in typeIds:
                Logger.cPrint(Logger.WARNING_TYPE, methodName
                            , f"'{T.extentK}' has unknown id in '{questionStr}'.")
                # qJson[T.validK] = "F"

        # [SC] validate 'transformations'
        if T.transformK not in qJson[T.cctransK]:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"'{T.transformK}' not found for '{questionStr}'.")
            qJson[T.validK] = "F"
        elif not isinstance(qJson[T.cctransK][T.transformK], list):
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"'{T.transformK}' is not a list in '{questionStr}'.")
            qJson[T.validK] = "F"
        elif len(qJson[T.cctransK][T.transformK]) == 0:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"'{T.transformK}' should have at least one transformation in '{questionStr}'.")
            qJson[T.validK] = "F"
        else:
            # [SC] validate each transformation object
            for trans in qJson[T.cctransK][T.transformK]:
                if T.beforeK not in trans:
                    Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'{T.beforeK}' is missing for transformation in '{questionStr}'.")
                    qJson[T.validK] = "F"
                elif not isinstance(trans[T.beforeK], list):
                    Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'{T.beforeK}' is not a list in '{questionStr}'.")
                    qJson[T.validK] = "F"
                elif len(trans[T.beforeK]) == 0:
                    Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'{T.beforeK}' is an empty list in '{questionStr}'.")
                    qJson[T.validK] = "F"
                else:
                    for beforeId in trans[T.beforeK]:
                        if beforeId not in typeIds:
                            Logger.cPrint(Logger.ERROR_TYPE, methodName
                                        , f"'{T.beforeK}' has unknown 'id={beforeId}' in '{questionStr}'.")
                            qJson[T.validK] = "F"

                if T.afterK not in trans:
                    Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'{T.afterK}' is missing for transformation in '{questionStr}'.")
                    qJson[T.validK] = "F"
                elif not isinstance(trans[T.afterK], list):
                    Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'{T.afterK}' is not a list in '{questionStr}'.")
                    qJson[T.validK] = "F"
                elif len(trans[T.afterK]) != 1:
                    Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'{T.afterK}' should have exactly one value in '{questionStr}'.")
                    qJson[T.validK] = "F"
                elif trans[T.afterK][0] not in typeIds:
                    Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'{T.afterK}' has unknown 'id={trans[T.afterK][0]}' in '{questionStr}'.")
                    qJson[T.validK] = "F"

                if T.keyK in trans:
                    if not isinstance(trans[T.keyK], str):
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"'{T.keyK}' is not a string for transformation '{trans}' in '{questionStr}'.")
                        qJson[T.validK] = "F"
                    elif trans[T.keyK] not in typeIds:
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"'{T.keyK}' has unknown 'id={trans[T.keyK]}' for transformation '{trans}' in '{questionStr}'.")
                        qJson[T.validK] = "F"


    # [SC] Returns True if two rules are identical (value-wise)
    # @param:  dictionary  ruleOne      A JSON object for the first rule.
    # @param:  dictionary  ruleTwo      A JSON object for the second rule.
    # @return: boolean                  True or False
    def sameRule(self, ruleOne, ruleTwo):
        methodName = "TypesToQueryConverter.sameRule"

        if not (ruleOne and ruleTwo):
            return False

        if not self.sameLHS(ruleOne[T.lhsK], ruleTwo[T.lhsK]):
            return False

        if ruleOne[T.rhsK] != ruleTwo[T.rhsK]:
            return False

        return True


    # [SC] Returns True if two LHS statements are identical (value-wise)
    # @param:  dictionary  qLhs        A JSON object for LHS created from a question type.
    # @param:  dictionary  ruleLhs     A JSON object of a rule's LHS.
    # @return: boolean                 True or False
    def sameLHS(self, qLhs, ruleLhs):
        methodName = "TypesToQueryConverter.sameLHS"

        # [SC] compare types
        if qLhs[T.typeK].lower() != ruleLhs[T.typeK].lower():
            return False

        # [SC] compare measureLevel
        if T.measureK in qLhs and T.measureK not in ruleLhs:
            return False
        elif T.measureK not in qLhs and T.measureK in ruleLhs:
            return False
        elif T.measureK in qLhs and T.measureK in ruleLhs:
            if qLhs[T.measureK].lower() != ruleLhs[T.measureK].lower():
                return False

        # [SC] compare inputType
        if T.inputTypeK in qLhs and T.inputTypeK not in ruleLhs:
            return False
        elif T.inputTypeK not in qLhs and T.inputTypeK in ruleLhs:
            return False
        elif T.inputTypeK in qLhs and T.inputTypeK in ruleLhs:
            if len(qLhs[T.inputTypeK]) == len(ruleLhs[T.inputTypeK]):
                qLhs[T.inputTypeK].sort()
                ruleLhs[T.inputTypeK].sort()
                for indexVal in range(len(ruleLhs[T.inputTypeK])):
                    if qLhs[T.inputTypeK][indexVal].lower() != ruleLhs[T.inputTypeK][indexVal].lower():
                        return False
            else:
                return False

        # [SC] compare key
        if T.keyK in qLhs and T.keyK not in ruleLhs:
            return False
        elif T.keyK not in qLhs and T.keyK in ruleLhs:
            return False
        elif T.keyK in qLhs and T.keyK in ruleLhs:
            if qLhs[T.keyK].lower() != ruleLhs[T.keyK].lower():
                return False

        return True


    # [SC] From a given question type, creates dictionary object representing LHS statement of a rule
    # @param:  dictionary  parsedTypeObj   A JSON object of the question type.
    # @param:  dictionary  qJson           A JSON object of the question annotation.
    # @return: dictionary                  returns the created LHS object
    def createLhs(self, parsedTypeObj, qJson):
        methodName = "TypesToQueryConverter.createLhs"

        if T.validK not in qJson:
            self.isValidQJson(qJson)
        if qJson[T.validK] != "T":
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Cannot create LHS statement. Invalid JSON structure. None returned.")
            return None

        # [SC] add type information; assumed that type contains exactly one value
        tempLhs = {T.typeK: parsedTypeObj[T.typeK]}

        # [SC] add measureLevel information if it exists in the question type annotation
        if T.measureK in parsedTypeObj:
            tempLhs[T.measureK] = parsedTypeObj[T.measureK]

        # [SC] add inputType information if the current type is an output
        inputTypes = []
        for transformation in qJson[T.cctransK][T.transformK]:
            # [SC] in after part, id with '_u' suffix is different from the id without the suffix,
            # that is, given {"before": ["2","3"],"after": ["3_u"]},
            # '2' and '3' are not considered as input for '3'

            # [SC] if true then this transformmation has the current type as the 'after' value
            if transformation[T.afterK][0] == parsedTypeObj[T.idK]:
                # [SC] iterate through the before Ids
                for beforeId in transformation[T.beforeK]:
                    # [SC] id with '_u' suffix is a valid input type
                    beforeId = beforeId.replace('_u', '')
                    for inputTypeObj in qJson[T.cctransK][T.typesK]:
                        if inputTypeObj[T.idK] == beforeId:
                            inputTypes.append(inputTypeObj[T.typeK])

                # [SC] if there is a 'key' json object then add it to the new LHS
                if T.keyK in transformation:
                    # [SC] extract key's type
                    for keyTypeObj in qJson[T.cctransK][T.typesK]:
                        if keyTypeObj[T.idK] == transformation[T.keyK]:
                            tempLhs[T.keyK] = keyTypeObj[T.typeK]
                            break
                    # [SC] sanity check; make sure the key's type was successfully extracted
                    if T.keyK not in tempLhs:
                        Logger.cPrint(Logger.ERROR_TYPE, methodName
                                    , f"Cannot find the type for the key '{transformation[T.keyK]}' " +
                                    f"of the type object '{parsedTypeObj}' in {qJson[T.questionK]}. " +
                                    "Assigning 'NA' value to the key's type.")
                        tempLhs[T.keyK] = 'NA'

        if inputTypes:
            tempLhs[T.inputTypeK] = inputTypes

        return tempLhs


    # [SC] Given question annotations, generates templates for rules using the types info in each question annotation.
    # @param:  list        parsedQuestions     A list of JSON objects annotating question.
    # @param:  dictionary  ruleTemplates       A JSON dictionary to which the new rules should be added
    # @return: void
    def generateRuleTemplates(self, parsedQuestions, ruleTemplates):
        methodName = "TypesToQueryConverter.generateRuleTemplates"

        for qJson in parsedQuestions:
            self.isValidQJson(qJson)

            if qJson[T.validK] != "T":
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                            , f"Cannot generate rule template. Invalid JSON structure. "
                            + f"The question annotation is skipped. Annotation: {qJson}")
                continue

            # [SC] generate a rule for each type
            for parsedTypeObj in qJson[T.cctransK][T.typesK]:
                # [SC] generate a LHS of a new rule
                newLhs = self.createLhs(parsedTypeObj, qJson)

                # [SC] make sure a rule with the same LHS does not already exist
                uniqueFlag = True
                for rule in ruleTemplates:
                    if self.sameLHS(rule[T.lhsK], newLhs):
                        uniqueFlag = False
                        break
                if uniqueFlag:
                    ruleTemplates.append({T.idK: len(ruleTemplates) + 1
                                             , T.descrK: qJson[T.questionK]
                                             , T.lhsK: newLhs, T.rhsK: ''})


    # [SC] Adds a new rule to the existing list of rules. Checks for duplicates and inconsistencies beforehand.
    # @param:   dictionary  newRule         The new rule to be added.
    # @param:   list        existingRules   A list of existing rules.
    # @return:  boolean     True if the new rule was successfully added. False otherwise.
    def addNewRule(self, newRule, existingRules):
        methodName = "TypesToQueryConverter.addNewRule"

        duplicateRule = None
        for rule in existingRules:
            if self.sameLHS(rule[T.lhsK], newRule[T.lhsK]):
                duplicateRule = rule
                break

        if duplicateRule:
            # Logger.cPrint(Logger.WARNING_TYPE, methodName
            #               , f"Duplicate rule:"
            #               + f"\n\tnew rule: {json.dumps(newRule, indent=4)}"
            #               + f"\n\told rule: {json.dumps(duplicateRule, indent=4)}\n.")
            if not duplicateRule[T.rhsK]:
                duplicateRule[T.rhsK] = newRule[T.rhsK]
                Logger.cPrint(Logger.WARNING_TYPE, methodName
                              , f"Transfered RHS from the new to the old rule:"
                              + f"\n\tnew rule: {json.dumps(newRule, indent=4)}"
                              + f"\n\told rule: {json.dumps(duplicateRule, indent=4)}\n.")
            elif newRule[T.rhsK] and duplicateRule[T.rhsK] != newRule[T.rhsK]:
                Logger.cPrint(Logger.WARNING_TYPE, methodName
                              , f"Iconsistent RHS found:"
                              + f"\n\tnew rule: {json.dumps(newRule, indent=4)}"
                              + f"\n\told rule: {json.dumps(duplicateRule, indent=4)}\n.")
            return False
        else:
            existingRules.append(newRule)
            return True


    # [SC] Derives news rules from the rules in 'existingRules' based on subtypes of input types.
    #       The new rules are added to 'existingRules'.
    # @param    list    existingRules   List of existing rules from which to derive the new rules.
    # @return:  void
    def expandRulesByInputTypeHiearchy(self, existingRules):
        methodName = "TypesToQueryConverter.expandRulesByInputTypeHiearchy"

        if not hConceptHierarchy:
            return

        if not existingRules:
            return

        # [SC] this list will temporarily contain new rules before they added to the master list
        newRules = []

        for rule in existingRules:
            lhsObj = rule[T.lhsK]

            if T.inputTypeK not in lhsObj:
                continue

            # [SC] generate a list of subtypes for each input type
            subTypeLists = []
            for type in lhsObj[T.inputTypeK]:
                typeObj = hConceptHierarchy[type]
                subTypes = [type]
                subTypes.extend(typeObj.getAllChildrenStr())
                subTypeLists.append(subTypes)

            # [SC] generate all combination of input types based on subtypes
            # [SC] note that duplicates such as [A,B] and [B,A] are possible
            inputTypeCombos = []
            self.getAllCombos(inputTypeCombos, [], 0, subTypeLists)

            # [SC] generate a new rule for each combination of subtypes
            for index in range(len(inputTypeCombos)):
                newRule = self.cloneRule(rule)
                newRule[T.lhsK][T.inputTypeK] = inputTypeCombos[index]
                newRule[T.idK] = f"{newRule[T.idK]}-IT{index}"
                newRule[T.descrK] = "Derived based on inputType substypes"
                newRules.append(newRule)

        # [SC] before adding each new rule make sure a rule with the same LHS does not already exist
        # [SC] also ignores duplicates from 'inputTypeCombos'
        newRulesAdded = 0
        for newRule in newRules:
            if self.addNewRule(newRule, existingRules):
                newRulesAdded += 1

        Logger.cPrint(Logger.INFO_TYPE, methodName
                    , f"{newRulesAdded} new rules were added.")


    # [SC] Derives news rules from the rules in 'existingRules' based on subtypes of measurement levels.
    #       The new rules are added to 'existingRules'.
    # @param    list    existingRules   List of existing rules from which to derive the new rules.
    # @return:  void
    def expandRulesByMeasureHiearchy(self, existingRules):
        methodName = "TypesToQueryConverter.expandRulesByMeasureHiearchy"
        regExp = "R\(\s?(?P<rOne>.+)\s?,\s?(?P<rTwo>.+)\s?\)"

        if not measureHierarchy:
            return

        if not existingRules:
            return

        # [SC] this list will temporarily contain new rules before they added to the master list
        newRules = []

        for rule in existingRules:
            matches = None
            lhsObj = rule[T.lhsK]

            if T.measureK not in lhsObj:
                continue

            # [SC] later will be used to change the cct expression to include the subtype
            if T.rhsK in rule:
                matches = re.search(regExp, rule[T.rhsK])
                if not matches:
                    Logger.cPrint(Logger.WARNING_TYPE, methodName
                                  , f"Rule with 'id={rule[T.idK]}' has invalid RHS value '{rule[T.rhsK]}'")

                if matches.group("rTwo") not in measureHierarchy:
                    matches = None

            # [SC] generate a list of subtypes for the measurement level
            subTypeLists = measureHierarchy[lhsObj[T.measureK]].getAllChildrenStr()

            # [SC] generate a new rule for each subtypes
            for index in range(len(subTypeLists)):
                newRule = self.cloneRule(rule)
                newRule[T.lhsK][T.measureK] = subTypeLists[index]
                newRule[T.idK] = f"{newRule[T.idK]}-ML{index}"
                newRule[T.descrK] = "Derived based on measureLevel substypes"
                newRules.append(newRule)

                if not matches:
                    continue

                superCCT = measureHierarchy[measureHierarchy[lhsObj[T.measureK]].cctStr]
                subCCT = measureHierarchy[measureHierarchy[subTypeLists[index]].cctStr]
                currCCT = measureHierarchy[matches.group("rTwo")]

                if superCCT != currCCT:
                    # [SC] the cct measurement level is lower than (child of) the type measurement level
                    if currCCT.hasParent(superCCT.conceptStr):
                        if subCCT.hasParent(currCCT.conceptStr):
                            newRule[T.rhsK] = f"R({matches.group('rOne')},{subCCT.conceptStr})"
                    # [SC] the cct measurement level is higher than (parent of) the type measurement level
                    # elif currCCT.hasChild(superCCT.conceptStr):
                    #    [SC] do nothing; assume the cct measurement level is the lowest possible annotation level
                else:
                    newRule[T.rhsK] = f"R({matches.group('rOne')},{subCCT.conceptStr})"

        # [SC] before adding each new rule make sure a rule with the same LHS does not already exist
        newRulesAdded = 0
        for newRule in newRules:
            if self.addNewRule(newRule, existingRules):
                newRulesAdded += 1

        Logger.cPrint(Logger.INFO_TYPE, methodName
                    , f"{newRulesAdded} new rules were added.")


    # [SC] Creates and returns a deep copy of a given rule.
    # @param:   dictionary  rule    The rule to be cloned.
    # @return:  dictionary          The deep copy rule.
    def cloneRule(self, rule):
        methodName = "TypesToQueryConverter.cloneRule"

        clonedRule = {T.idK: rule[T.idK],
                      T.descrK: rule[T.descrK],
                      T.lhsK: {},
                      T.rhsK: rule[T.rhsK]}

        clonedRule[T.lhsK][T.typeK] = rule[T.lhsK][T.typeK]

        if T.measureK in rule[T.lhsK]:
            clonedRule[T.lhsK][T.measureK] = rule[T.lhsK][T.measureK]

        if T.keyK in rule[T.lhsK]:
            clonedRule[T.lhsK][T.keyK] = rule[T.lhsK][T.keyK]

        if T.inputTypeK in rule[T.lhsK]:
            clonedRule[T.lhsK][T.inputTypeK] = []
            for type in rule[T.lhsK][T.inputTypeK]:
                clonedRule[T.lhsK][T.inputTypeK].append(type)

        return clonedRule


    # [SC] Creates all possible combbinations of inputs types. All combos are added to 'allCombos' list.
    #       Note that [A,B] and [B,A] are considered as different combos.
    # @param:   list        allCombos       A list of lists. Each nested list is a combo of input types.
    # @param:   list        inputTypes      Contains the current combo of input types being created.
    # @param:   list        subTypeLists    A list of lists. Each nested list coressponds to one input
    #                                       and contains legible subtypes for that input.
    # @param:   integer     index           Index of a list in 'subTypeLists' that is being currently used
    #                                       to create a combo in 'inputTypes'.
    # @return:  void
    def getAllCombos(self, allCombos, inputTypes, index, subTypeLists):
        methodName = "TypesToQueryConverter.getAllCombos"

        for type in subTypeLists[index]:
            cloneInputTypes = list(inputTypes)
            cloneInputTypes.append(type)
            if index < len(subTypeLists) - 1:
                self.getAllCombos(allCombos, cloneInputTypes, index + 1, subTypeLists)
            else:
                allCombos.append(cloneInputTypes)


    # [SC] annotates question's cctrans types with algebra expressions
    # @param:  dictionary  qJson   A JSON object of the question annotation.
    # @return: void
    def typesToCCT(self, qJson):
        # [SC][TODO] check if the rules were loaded
        # [SC][TODO] make sure every type is annotated with cct before returning True

        methodName = "TypesToQueryConverter.typesToCCT"

        if T.validK not in qJson:
            self.isValidQJson(qJson)

        if qJson[T.validK] != "T":
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Cannot generate '{T.cctK}' for {qJson}. Invalid JSON structure.")
            qJson.pop(T.validK)
            return False
        qJson.pop(T.validK)

        # [SC] sanity check
        if not self.isRulesLoaded():
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Rules for annotating with algebra expressions are not loaded.")
            return False
        if not self.isConsistentRules():
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Rules for annotating with algebra expressions are not consistent.")
            return False

        # [SC] iterate through the question types
        for parsedTypeObj in qJson[T.cctransK][T.typesK]:
            # [SC] create LHS object for the question type and compare it with rules' LHSs
            tempLhs = self.createLhs(parsedTypeObj, qJson)

            annotatedF = False
            # [SC] iterate through the rules
            for convRule in convRules:
                if self.sameLHS(tempLhs, convRule[T.lhsK]):
                    # [SC] matching rule; add annotate with the algebra expression
                    parsedTypeObj[T.cctK] = convRule[T.rhsK]
                    annotatedF = True
                    break

            if not annotatedF:
                Logger.cPrint(Logger.WARNING_TYPE, methodName
                                , f"No matching rule to annotate '{parsedTypeObj}' in '{qJson[T.questionK]}'.")

        for parsedTypeObj in qJson[T.cctransK][T.typesK]:
            if T.cctK not in parsedTypeObj:
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'Not all types were annotated with algebra expression for '{qJson[T.questionK]}'.")
                return False

        return True


    # [SC][TODO] this a temporary method for testing and debugging rules only
    def typesToCCTDebug(self, qJson, missingRuleList):
        # [SC][TODO] check if the rules were loaded
        # [SC][TODO] make sure every type is annotated with cct before returning True

        methodName = "TypesToQueryConverter.typesToCCT"

        if T.validK not in qJson:
            self.isValidQJson(qJson)

        if qJson[T.validK] != "T":
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Cannot generate '{T.cctK}' for {qJson}. Invalid JSON structure.")
            qJson.pop(T.validK)
            return False
        qJson.pop(T.validK)

        # [SC] sanity check
        if not self.isRulesLoaded():
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Rules for annotating with algebra expressions are not loaded.")
            return False
        if not self.isConsistentRules():
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Rules for annotating with algebra expressions are not consistent.")
            return False

        # [SC] iterate through the question types
        for parsedTypeObj in qJson[T.cctransK][T.typesK]:
            # [SC] create LHS object for the question type and compare it with rules' LHSs
            tempLhs = self.createLhs(parsedTypeObj, qJson)

            annotatedF = False
            # [SC] iterate through the rules
            for convRule in convRules:
                if self.sameLHS(tempLhs, convRule[T.lhsK]):
                    # [SC] matching rule; add annotate with the algebra expression
                    parsedTypeObj[T.cctK] = convRule[T.rhsK]
                    annotatedF = True
                    break

            if not annotatedF:
                Logger.cPrint(Logger.WARNING_TYPE, methodName
                                , f"No matching rule to annotate '{parsedTypeObj}' in '{qJson[T.questionK]}'.")

                existsF = False
                for currRule in missingRuleList:
                    if self.sameLHS(tempLhs, currRule[T.lhsK]):
                        existsF = True
                if not existsF:
                    missingRuleList.append(
                        {
                            T.idK: ""
                            , T.descrK: qJson[T.questionK]
                            , T.lhsK: tempLhs
                            , T.rhsK: ""
                        }
                    )

        for parsedTypeObj in qJson[T.cctransK][T.typesK]:
            if T.cctK not in parsedTypeObj:
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                                , f"'Not all types were annotated with algebra expression for '{qJson[T.questionK]}'.")
                return False

        return True


    # [SC] generates a JSON query based on 'cctrans' and 'cct'
    # @param:  dictionary   qJson       A JSON object of the question annotation.
    # @param:  boolean      validate    It True the question annotation is checked for a valid structure.
    # @param:  boolean      annotate    If True the types are annotated with 'cct' expressions.
    # @return: void                     adds 'query' object to qJson
    def algebraToQuery(self, qJson, validate, annotate):
        methodName = "TypesToQueryConverter.algebraToQuery"

        if validate:
            self.isValidQJson(qJson)
            if qJson[T.validK] != "T":
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                            , f"Cannot generate query for {qJson}. Invalid JSON structure.")
                qJson.pop(T.validK)
                return
            qJson.pop(T.validK)

        if annotate:
            # [SC] sanity check
            if not self.typesToCCT(qJson):
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                            , f"Cannot annotate types with algebra expressions for '{qJson[T.questionK]}'.")
                return

        trans = qJson[T.cctransK][T.transformK]
        types = qJson[T.cctransK][T.typesK]
        # [SC] id of the type that is the final output of the transformations
        rootTypeId = None

        # [SC] this dictionary contains a JSON query block for each type
        # key is a type id and value is a JSON query block
        jsonQueryBlocks = {}
        for typeObj in types:
            jsonQueryBlocks[typeObj[T.idK]] = typeObj[T.cctK]

        # [SC] 1. add to 'jsonQueryBlocks' derived types with '_u' suffix
        # [SC] 2. collect IDs of all derived types
        derivedId = []
        for transObj in trans:
            afterId = transObj[T.afterK][0]
            # [SC] 1. add to 'jsonQueryBlocks' derived types with '_u' suffix
            if afterId not in jsonQueryBlocks.keys():
                afterIdAlias = afterId.replace('_u', '')
                if afterIdAlias in jsonQueryBlocks.keys():
                    jsonQueryBlocks[afterId] = jsonQueryBlocks[afterIdAlias]
                else:
                    jsonQueryBlocks[afterId] = ""
            # [SC] 2. collect IDs of all derived types
            derivedId.append(afterId)
        # [SC] change the list into a set
        derivedId = set(derivedId)

        while derivedId:
            # [SC] create json query parts for each transformation
            # that has its 'before' types has already been derived
            for transObj in trans:
                # [SC] check via intersection if any value in 'before' yet to be derived
                if not set(transObj[T.beforeK]) & derivedId:
                    # [SC] create a query JSON block
                    queryBlock = {
                        T.afterIdK: transObj[T.afterK][0],
                        T.afterK: jsonQueryBlocks[transObj[T.afterK][0]],
                        T.beforeK: []
                    }

                    # [SC] retrieve existing query blocks to construct the before part
                    for beforeId in transObj[T.beforeK]:
                        queryBlock[T.beforeK].append(jsonQueryBlocks[beforeId])

                    # [SC] update the query block dictionary with the new block
                    jsonQueryBlocks[queryBlock[T.afterIdK]] = queryBlock

                    # [SC] the last type to be derived is always the root type
                    if len(derivedId) == 1:
                        rootTypeId = queryBlock[T.afterIdK]

                    # [SC] remove the current type id from the to be derived list
                    derivedId.discard(queryBlock[T.afterIdK])

        # [SC] query block for the root type is always the compelte query
        finalQuery = jsonQueryBlocks[rootTypeId]
        qJson[T.queryK] = finalQuery


    # [SC] generates a JSON query based on 'cctrans' and 'cct'
    # @param:  dictionary   qJson       A JSON object of the question annotation.
    # @param:  boolean      validate    It True the question annotation is checked for a valid structure.
    # @param:  boolean      annotate    If True the types are annotated with 'cct' expressions.
    # @return: void                     adds 'query' object to qJson
    def algebraToExpandedQuery(self, qJson, validate, annotate):
        methodName = "TypesToQueryConverter.algebraToExpandedQuery"

        if validate:
            self.isValidQJson(qJson)
            if qJson[T.validK] != "T":
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                              , f"Cannot generate query for {qJson}. Invalid JSON structure.")
                qJson.pop(T.validK)
                return
            qJson.pop(T.validK)

        if annotate:
            # [SC] sanity check
            if not self.typesToCCT(qJson):
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                              , f"Cannot annotate types with algebra expressions for '{qJson[T.questionK]}'.")
                return

        trans = qJson[T.cctransK][T.transformK]
        types = qJson[T.cctransK][T.typesK]

        # [SC] this dictionary contains a JSON query block for each type
        # key is a type id and value is a JSON query block
        jsonQueryBlocks = {}
        for typeObj in types:
            jsonQueryBlocks[typeObj[T.idK]] = {
                T.afterK: {
                    "id": typeObj[T.idK],
                    "cct": typeObj[T.cctK]
                }
            }

        # [SC] contains all ids that occure in 'before' and 'after' parts
        beforeIdList = []
        afterIdList = []
        # [SC] add 'before' parts to the query blocks
        for transObj in trans:
            outputQueryObj = jsonQueryBlocks[transObj[T.afterK][0]]

            # [SC] add 'before' query object
            beforeQueryObj = []
            for beforeId in transObj[T.beforeK]:
                beforeQueryObj.append(jsonQueryBlocks[beforeId])
            outputQueryObj[T.beforeK] = beforeQueryObj

            # [SC] add 'key' to the query block
            if T.keyK in transObj:
                outputQueryObj[T.afterK][T.keyK] = transObj[T.keyK]

            beforeIdList.extend(transObj[T.beforeK])
            afterIdList.extend(transObj[T.afterK])

        # [SC] find the root; root id is after id that is not among before ids
        for keyVal in jsonQueryBlocks.keys():
            if keyVal not in beforeIdList and keyVal in afterIdList:
                # [SC] query block for the root type is always the compelte query
                qJson[T.queryExK] = jsonQueryBlocks[keyVal]



rootPath = ""

# [SC] load the rules for annotating with cct expressions
conversionRulesPath = f'{rootPath}Rules/conversionRules.json'
convRules = json.load(open(conversionRulesPath))

# [SC] load concept type hierachy
hConceptHierarchyPath = f'{rootPath}Rules/hConceptHierarchy.json'
hConceptHierarchyJson = json.load(open(hConceptHierarchyPath))
hConceptHierarchy = {}

# [SC] load measurement hierachy
measureHierarchyPath = f'{rootPath}Rules/measureHierarchy.json'
measureHierarchyJson = json.load(open(measureHierarchyPath))
measureHierarchy = {}


def parseHiearchy(hierarchyJson, hiearchyDict):
    methodName = "parseHiearchy"

    if not hierarchyJson:
        Logger.cPrint(Logger.ERROR_TYPE, methodName
                      , f"Cannot create concept hierarchy. 'hierarchyJson' is empty.")
        return

    if not isinstance(hiearchyDict, dict):
        Logger.cPrint(Logger.ERROR_TYPE, methodName
                      , f"Cannot create concept hierarchy. 'hiearchyDict' is not dictionary.")
        return

    for term in hierarchyJson[T.termsK]:
        if term[T.conceptK] not in hiearchyDict:
            hiearchyDict[term[T.conceptK]] = HConcept(term[T.conceptK], term[T.cctK])
        else:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                        , f"Cannot create concept hierarchy. Duplicate concept '{term[T.conceptK]}' found.")
            return

    for relation in hierarchyJson[T.hierarchyK]:
        if relation[T.superK] not in hiearchyDict:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                          , f"Cannot create concept hierarchy. '{relation[T.superK]}' not found among terms.")
            return

        if relation[T.subK] not in hiearchyDict:
            Logger.cPrint(Logger.ERROR_TYPE, methodName
                          , f"Cannot create concept hierarchy. '{relation[T.subK]}' not found among terms.")
            return

        superC = hiearchyDict[relation[T.superK]]
        subC = hiearchyDict[relation[T.subK]]

        superC.children.append(subC)
        subC.parents.append(superC)


# [SC] this function needs to be called during module init
def parseHierarchies():
    parseHiearchy(measureHierarchyJson, measureHierarchy)
    parseHiearchy(hConceptHierarchyJson, hConceptHierarchy)


# [SC] for testing purpose only
if __name__ == '__main__':
    parseHierarchies()

    converter = TypesToQueryConverter()




    # with open(f'{rootPath}Rules/Haiqi/ParseResults_GeoAnQu.json', 'r') as baseFile:
    #     with open(f'{rootPath}ParseResults_GeoAnQu.json', 'r') as newFile:
    #         baseJson = json.load(baseFile)
    #         newJson = json.load(newFile)
    #
    #         for index in range(len(baseJson)):
    #             baseQ = baseJson[index]
    #             newQ = newJson[index]
    #
    #             baseStr = json.dumps(baseQ['cctrans'], indent=4)
    #             newStr = json.dumps(newQ['cctrans'], indent=4)
    #
    #             if baseStr != newStr:
    #                 print(f"inconsistent {baseQ[T.questionK]}")


    # with open(f'{rootPath}Rules/GeoAnQu_parser_results_1024.json', 'r') as geoanquFile:
    #     geoanquJson = json.load(geoanquFile)
    #
    #     for qJson in geoanquJson:
    #         converter.isValidQJson(qJson)
    #
    #     missingRules = []
    #     for qJson in geoanquJson:
    #         converter.typesToCCTDebug(qJson, missingRules)
    #
    #     print(len(missingRules))
    #     with open(f"{rootPath}Rules/GeoAnQu_parser_results_1024_cct.json", 'w') as outfile:
    #         outfile.write(json.dumps(geoanquJson, indent=4))
    #     with open(f"{rootPath}Rules/missingRules.json", 'w') as outfile:
    #         outfile.write(json.dumps(missingRules, indent=4))


    with open(f'{rootPath}Rules/conversionRules.json', 'r') as rulesFile:
        rulesJson = json.load(rulesFile)
        converter.expandRulesByInputTypeHiearchy(rulesJson)
        converter.expandRulesByMeasureHiearchy(rulesJson)
        with open(f"{rootPath}Rules/conversionRules_extended.json", 'w') as outfile:
            outfile.write(json.dumps(rulesJson, indent=4))


    # converter.expandRulesByInputTypeHiearchy(convRules)
    # with open(f"{rootPath}Rules/Haiqi/conversionRules_extendedTypes.json", 'w') as outfile:
    #     outfile.write(json.dumps(convRules, indent=4))
    #
    # converter.expandRulesByMeasureHiearchy(convRules)
    # with open(f"{rootPath}Rules/Haiqi/conversionRules_extendedMeasures.json", 'w') as outfile:
    #     outfile.write(json.dumps(convRules, indent=4))


    # with open(f'{rootPath}Rules/Haiqi/conversionRules_extendedTypes.json', 'r') as rulesOneFile:
    #     rulesOne = json.load(rulesOneFile)
    #     with open(f'{rootPath}Rules/Haiqi/conversionRules_extendedTypes_base.json', 'r') as rulesTwoFile:
    #         rulesTwo = json.load(rulesTwoFile)
    #
    #         matches = 0
    #         for ruleOne in rulesOne:
    #             for ruleTwo in rulesTwo:
    #                 if converter.sameRule(ruleOne, ruleTwo):
    #                     matches += 1
    #                     rulesTwo.remove(ruleTwo)
    #
    #         print(f"total matches: {matches} from {len(rulesOne)}")
    #         print(rulesTwo)


    with open(f'{rootPath}Rules/Haiqi/prototype questions.json', 'r') as protoQuestionFile:
        parsedQuestions = json.load(protoQuestionFile)
        for qJson in parsedQuestions:
            converter.algebraToQuery(qJson, True, True)
            converter.algebraToExpandedQuery(qJson, False, False)
        with open(f"{rootPath}Rules/Haiqi/prototype questions_QUERY.json", 'w') as outfile:
            outfile.write(json.dumps(parsedQuestions, indent=4))


    # with open(f'{rootPath}Rules/Haiqi/prototype questions.json', 'r') as protoQuestionFile:
    #     parsedQuestions = json.load(protoQuestionFile)
    #     ruleTemplates = []
    #     converter.generateRuleTemplates(parsedQuestions, ruleTemplates)
    #     with open(f"{rootPath}Rules/Haiqi/ruleTemplatesTest.json", 'w') as outfile:
    #         outfile.write(json.dumps(ruleTemplates, indent=4))


    # with open(f'{rootPath}Rules/Haiqi/prototype questions.json', 'r') as protoQuestionFile:
    #     parsedQuestions = json.load(protoQuestionFile)
    #     for qJson in parsedQuestions:
    #         converter.isValidQJson(qJson)

    # with open(f'{rootPath}Rules/Haiqi/prototype questions_CCT.json', 'r') as protoQuestionFile:
    #     parsedQuestions = json.load(protoQuestionFile)
    #     for qJson in parsedQuestions:
    #         converter.isValidQJson(qJson)

    # with open(f'{rootPath}Rules/Haiqi/testQJson.json', 'r') as protoQuestionFile:
    #     parsedQuestions = json.load(protoQuestionFile)
    #     for qJson in parsedQuestions:
    #         converter.isValidQJson(qJson)
    #         print(qJson[T.validK])


    # lhsOne = {T.typeK: 'object'}
    # lhsTwo = {T.typeK: 'field'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object'}
    # lhsTwo = {T.typeK: 'object'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era'}
    # lhsTwo = {T.typeK: 'object'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    # print(converter.sameLHS(lhsTwo, lhsOne))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era'}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'ira'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era'}
    # lhsTwo = {T.typeK: 'field', T.measureK: 'era'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'field', T.measureK: 'era'}
    # lhsTwo = {T.typeK: 'field', T.measureK: 'era'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    # print(converter.sameLHS(lhsTwo, lhsOne))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field", "object"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "object"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "object", "field"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field", "object"]}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "object", "field"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field"], T.keyK: 'field'}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field", "object"]}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    # print(converter.sameLHS(lhsTwo, lhsOne))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field"], T.keyK: 'field'}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field", "object"], T.keyK: 'object'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))
    # print(converter.sameLHS(lhsTwo, lhsOne))
    #
    # lhsOne = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["object", "field"], T.keyK: 'field'}
    # lhsTwo = {T.typeK: 'object', T.measureK: 'era', T.inputTypeK: ["field", "object"], T.keyK: 'field'}
    # print(f"\ncomparing \n{lhsOne}\n{lhsTwo}")
    # print(converter.sameLHS(lhsOne, lhsTwo))

    # hiearchyDict = hConceptHierarchy
    # hiearchyDict = measureHierarchy
    # for conceptObj in hiearchyDict.values():
    #     print(f"####################### Concept '{conceptObj.conceptStr}/{conceptObj.cctStr}' has")
    #
    #     parents = []
    #     for parentObj in conceptObj.parents:
    #         parents.append(parentObj.conceptStr)
    #
    #     children = []
    #     for childObj in conceptObj.children:
    #         children.append(childObj.conceptStr)
    #
    #     print(f"supertypes '{parents}'")
    #     print(f"subtypes '{children}'")
    #     print("")

    # for index in range(1, 10):
    #     for indexTwo in range(1, 10):
    #         print(f"p{index} has parent p{indexTwo}: {hConceptHierarchy[f'p{index}'].hasParent(f'p{indexTwo}')}")
    #     print("")
    #
    # for index in range(1, 10):
    #     for indexTwo in range(1, 10):
    #         print(f"p{index} has child p{indexTwo}: {hConceptHierarchy[f'p{index}'].hasChild(f'p{indexTwo}')}")
    #     print("")
    #
    # for index in range(1, 10):
    #     print(f"parents for p{index}: {hConceptHierarchy[f'p{index}'].getAllParentsStr()}")
    # print("")
    #
    # for index in range(1, 10):
    #     print(f"children for p{index}: {hConceptHierarchy[f'p{index}'].getAllChildrenStr()}")
    # print("")