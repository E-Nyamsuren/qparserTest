import json
import re
import numpy
# [X] import nlp packages for placename and entities recognition
from spacy.lang.en import English
import en_core_web_sm
from spacy.matcher import PhraseMatcher
import nltk
import nltk.tokenize as nt
from allennlp.predictors.predictor import Predictor  # For using ELMo-based NER & Fine Grained NER
# import allennlp_models.tagging
from word2number import w2n
# [X] import antlr4 grammar
# [SC][DELETE] from antlr4 import *
from antlr4 import InputStream # [SC][ADDED]
from antlr4 import CommonTokenStream # [SC][ADDED]
from Grammar.GeoAnQuLexer import GeoAnQuLexer
from Grammar.GeoAnQuParser import GeoAnQuParser
from antlr4.tree.Trees import Trees

# from antlr4.error.ErrorListener import ErrorListener


# [X]  customized a list of stopwords
class CustomEnglishDefaults(English.Defaults):
    # stop_words = set(["is", "are", "was", "were", "do", "does", "did", "have", "had"])
    stop_words = {"do", "did", "does", "a", "an", "the", "their", 'his', 'her', 'my'}


class CustomEnglish(English):
    lang = "custom_en"
    Defaults = CustomEnglishDefaults


class BracketMatch:
    def __init__(self, refstr, parent=None, start=-1, end=-1):
        self.parent = parent
        self.start = start
        self.end = end
        self.refstr = refstr
        self.nested_matches = []

    def __str__(self):
        cur_index = self.start + 1
        result = ""
        if self.start == -1 or self.end == -1:
            return ""
        for child_match in self.nested_matches:
            if child_match.start != -1 and child_match.end != -1:
                result += self.refstr[cur_index:child_match.start]
                cur_index = child_match.end + 1
            else:
                continue
        result += self.refstr[cur_index:self.end]
        return result


class QuestionParser:
    def __init__(self, connInfo):
        self.connInfo = connInfo
        self.result = {}
        self.core_id = 0
        self.coreConTrans = {}  # final cctrans output


    def is_left_inside(self, string, list):
        cur_list = []
        for l in list:
            if l.lower().strip().startswith(string):
                cur_list.append(l)
        return cur_list


    # [X] Convert numeric words into digit numbers
    # Input sentence(string): 'What is average network distance for three thousand and five people to
    # two hundred and twelve closest primary schools'.
    # Output sentence(string): 'What is average network distance for 3005 people to 212 closest primary schools'.
    # except for 'five star hotels'
    def word2num(self, sentence):
        try:
            if 'five star' not in sentence:
                cur_doc = nlp(sentence)
                numWords = ''
                numDig = ''
                for cur_i in range(0, len(cur_doc)):
                    if cur_doc[cur_i].pos_ == 'NUM':
                        numWords = numWords + ' ' + cur_doc[cur_i].text
                        cur_i += 1
                    elif cur_doc[cur_i].text == 'and' and cur_doc[cur_i - 1].pos_ == 'NUM':
                        numWords = numWords + ' and'
                        cur_i += 1
                    elif numWords and not cur_doc[cur_i].pos_ == 'NUM':
                        numDig = w2n.word_to_num(numWords.strip())
                        # print(numWords)
                        # print(numDig)
                        sentence = sentence.replace(numWords.strip(), str(numDig))
                        numWords = ''
        except Exception as e:
            # [SC][TODO] error logging
            print("============================ Exception in word2num:")
            print(e)
            return sentence

        return sentence


    # [X] Identify Place names(e.g., ) in questions
    # input string sentence:
    # 'What buildings are within 1 minute of driving time from a fire station for
    # Multifunctional Urban Area in Fort Worth in US
    # output tuple:
    # (['Multifunctional Urban Area', 'Fort Worth', 'US'],
    # 'What buildings are within 1 minute of driving time from a fire station
    # for each PlaceName0 in PlaceName1 in PlaceName3')
    def place_ner(self, sentence):
        pred = predictorELMo.predict(sentence)

        PlaceName = []
        loc = 0
        for i in range(0, len(pred['tags'])):
            # place name is a single word, such as Utrecht
            # unsolved question: Which urban areas are within 150 miles of the Ogallala aquifer, have precipitation lower than 10 inches, and intersect with the irrigation regions in Ogallala (High Plains) Aquifer, US
            if pred['tags'][i] == 'U-LOC' or pred['tags'][i] == 'U-PER':
                if not pred['words'][i] == 'PC4':
                    PlaceName.append(pred['words'][i])
                    sentence = sentence.replace(pred['words'][i], 'PlaceName' + str(loc))
                    loc += 1
            elif pred['tags'][i] == 'B-LOC':  # When place name is a phrase, such as Happy Valley
                place = pred['words'][i]
            elif pred['tags'][i] == 'I-LOC' or pred['tags'][i] == 'L-LOC':
                place = place + ' ' + pred['words'][i]
                if i + 1 == len(pred['tags']):
                    PlaceName.append(place)
                    sentence = sentence.replace(place, 'PlaceName' + str(loc))
                    place = ''
                elif pred['tags'][i + 1] == 'O':  # 'O' not a place name
                    PlaceName.append(place)
                    sentence = sentence.replace(place, 'PlaceName' + str(loc))
                    loc += 1
                    place = ''

        #  allennlp fail to capture Oleander as city name
        cur_words2 = sentence.strip().split(' ')
        if 'Oleander' in cur_words2:
            sentence = sentence.replace('Oleander', 'PlaceName'+str(len(PlaceName)))
            PlaceName.append('Oleander')

        # Solve place name + place type, such as PlaceName0 area(PC4 area) -> PlaceName0(PC4 area)...
        cur_words = sentence.strip().split(' ')
        for i in range(0, len(cur_words)):
            if cur_words[i].startswith('PlaceName'):
                if i + 1 < len(cur_words):
                    if not len(self.is_left_inside(cur_words[i + 1],
                                                pt_set)) == 0:  # PlaceName0 ski resort(Happy Valley ski resort) -> PlaceName0
                        if i + 2 < len(cur_words):
                            cur_pt = cur_words[i + 1] + ' ' + cur_words[i + 2]
                            if cur_pt in self.is_left_inside(cur_words[i + 1], pt_set):
                                cur_index = int(cur_words[i][9:])  # PlaceName0 -> 0
                                PlaceName[cur_index] = PlaceName[cur_index] + ' ' + cur_pt
                                sentence = sentence.replace(' ' + cur_pt, '')
                            elif i + 3 < len(cur_words):
                                cur_pt = ' '.join(cur_words[i + 1:i + 4])
                                if cur_pt in self.is_left_inside(cur_words[i + 1], pt_set):
                                    cur_index = int(cur_words[i][9:])
                                    PlaceName[cur_index] = PlaceName[cur_index] + ' ' + cur_pt
                                    sentence = sentence.replace(' ' + cur_pt, '')
                                elif cur_words[i+1] in pt_set:
                                    cur_index = int(cur_words[i][9:])
                                    PlaceName[cur_index] = PlaceName[cur_index] + ' ' + cur_words[i + 1]
                                    sentence = sentence.replace(' '.join(cur_words[i:i + 2]), cur_words[i])
                    elif cur_words[i + 1] in pt_set:  # PlaceName0(Happy Valley) resort -> PlaceName0(Happy Valley resort)
                        cur_index = int(cur_words[i][9:])  # PlaceName0 -> 0
                        PlaceName[cur_index] = PlaceName[cur_index] + ' ' + cur_words[i + 1]
                        sentence = sentence.replace(' '.join(cur_words[i:i + 2]), cur_words[i])


        # print(sentence)
        # print(PlaceName)
        return PlaceName, sentence


    # [X] Identify Date, Time, Quantity, Percent
    # input string sentence:
    # 'What buildings are within 1 minute, 2 minutes and 3 minutes of driving time from 3 fire stations that are
    # within 60 meters of rivers and located at areas that has slope larger than 10 percent for each PlaceName1 in
    # PlaceName2 between 1990 and 2000'
    # output tuple:
    # ({'Time': [1 minute, 2 minutes, 3 minutes], 'Quantity': [60 meters],
    # 'Percent': [larger than 10 percent], 'Date': [between 1990 and 2000]},
    # 'What buildings are within ETime0, ETime1, and ETime2 of driving time from 3 fire stations that are within
    # EQuantity0 of rivers and located at areas that has slope EPercent1 for each PlaceName0 in PlaceName1 EDate0')
    def entity_ner(self, sentence):
        entities = []
        enti_dict = {}
        Date = []
        Time = []
        Quantity = []
        Percent = []

        cur_sen = ''
        if 'each' in sentence:  # {'Quantity': [each 50 square km]} -> {'Quantity': [50 square km]}
            cur_sen = sentence.replace(' each', '')
        else:
            cur_sen = sentence

        cur_doc = nlp(cur_sen)
        for i in cur_doc.ents:
            compBool = [word in i.text for word in compR]
            if True in compBool:
                tin = compBool.index(True)
                en_text = i.text.replace(compR[tin] + ' ', '')
                entities.append((en_text, i.label_))
            else:
                ilist = i.text.split(' ')
                if ilist[-1] == 'by':
                    entities.append((i.text.replace(' by', ''), i.label_))
                else:
                    entities.append((i.text, i.label_))

        D_loc = 0
        T_loc = 0
        Q_loc = 0
        P_loc = 0

        cardinal_sen = sentence.strip().split(' ')
        for i in range(0, len(entities)):
            if entities[i][1] == 'TIME':
                Time.append(entities[i][0])
                sentence = sentence.replace(entities[i][0], 'ETime' + str(T_loc))
                T_loc += 1
            elif entities[i][1] == 'QUANTITY':
                Quantity.append(entities[i][0])
                sentence = sentence.replace(entities[i][0], 'EQuantity' + str(Q_loc))
                Q_loc += 1
            elif entities[i][1] == 'CARDINAL' and entities[i][0].isnumeric() and cardinal_sen.index(entities[i][0]) + 1 < len(cardinal_sen) and \
                    cardinal_sen[cardinal_sen.index(entities[i][0]) + 1] in units:  # 70 db
                quan_words = entities[i][0] + ' ' + cardinal_sen[cardinal_sen.index(entities[i][0]) + 1]
                Quantity.append(quan_words)
                sentence = sentence.replace(quan_words, 'EQuantity' + str(Q_loc))
                Q_loc += 1
            elif entities[i][1] == 'CARDINAL' and  any(x in entities[i][0].split(' ') for x in units): #  [('between 700 and 2000 meters', 'CARDINAL')]
                Quantity.append(entities[i][0])
                sentence = sentence.replace(entities[i][0], 'EQuantity' + str(Q_loc))
                Q_loc += 1
            elif entities[i][1] == 'PERCENT':
                Percent.append(entities[i][0])
                sentence = sentence.replace(entities[i][0], 'EPercent' + str(P_loc))
                P_loc += 1
            elif entities[i][1] == 'DATE' and not entities[i][0] == 'annual' and not entities[i][0] == 'monthly' \
                    and not entities[i][0].startswith('PlaceName'):
                Date.append(entities[i][0])
                sentence = sentence.replace(entities[i][0], 'EDate' + str(D_loc))
                D_loc += 1

        cur_w = sentence.strip().split(' ')
        cur_quan = ''
        for w in cur_w:
            if w.startswith('meter') or w.startswith('millimeter'):
                cur_quan = cur_w[cur_w.index(w) - 1] + ' ' + w
                Quantity.append(cur_quan)
                sentence = sentence.replace(cur_quan, 'EQuantity' + str(Q_loc))
                Q_loc += 1
            elif w.isnumeric() and cur_w.index(w) < len(cur_w) - 3 and cur_w[cur_w.index(w) + 1] == 'per' and cur_w[
                cur_w.index(w) + 2] == 'square' and cur_w[cur_w.index(w) + 3].startswith(
                'kilometer'):  # 300 per square kilometer
                cur_quan = w + ' per square ' + cur_w[cur_w.index(w) + 3]
                Quantity.append(cur_quan)
                sentence = sentence.replace(cur_quan, 'EQuantity' + str(Q_loc))
                Q_loc += 1
            elif w == 'per' and cur_w.index(w) < len(cur_w) - 3 and cur_w[cur_w.index(w) - 1].isnumeric() and cur_w[
                cur_w.index(w) + 1].isnumeric():  # 500 per 1000000 people
                cur_quan = ' '.join(cur_w[cur_w.index(w) - 1: cur_w.index(w) + 3])
                Quantity.append(cur_quan)
                sentence = sentence.replace(cur_quan, 'EQuantity' + str(Q_loc))
                Q_loc += 1
            elif w.isnumeric() and cur_w[int(cur_w.index(w) - 1)] == 'over' and cur_w[
                int(cur_w.index(w) - 2)] in humanWords:
                Date.append('over ' + w)
                sentence = sentence.replace('over ' + w, 'EDate' + str(D_loc))
                D_loc += 1
            elif w.isnumeric() and cur_w[int(cur_w.index(w) - 1)] == 'than' and cur_w[
                int(cur_w.index(w) - 3)] in humanWords:
                cur_date = ' '.join(cur_w[cur_w.index(w) - 2: cur_w.index(w) + 1])
                Date.append(cur_date)
                sentence = sentence.replace(cur_date, 'EDate' + str(D_loc))
                D_loc += 1

        cur_words = sentence.strip().split(' ')
        if not len(Time) == 0:
            enti_dict['time'] = Time
        if not len(Quantity) == 0:
            for w in cur_words:
                if w.startswith('EQuantity'):
                    i = cur_words.index(w)
                    if cur_words[i - 1] == 'by' and cur_words[
                        i - 2].isnumeric():  # 2 by Quantity0(2 km) grid cell -> Quantity0 grid cell
                        Quantity[int(w[9])] = ' '.join(cur_words[i - 2:i]) + ' ' + Quantity[int(w[9])]
                        sentence = sentence.replace(' '.join(cur_words[i - 2:i]) + ' ' + w, w)
                        enti_dict['quantity'] = Quantity
                    elif cur_words[i - 1] == 'from':  # from Quantity0(60 to 600 meters) -> Quantity0
                        Quantity[int(w[9])] = 'from ' + Quantity[int(w[9])]
                        sentence = sentence.replace('from ' + w, w)
                        enti_dict['quantity'] = Quantity
                    elif cur_words[i - 1] == 'to' and cur_words[i - 2].isnumeric() and cur_words[
                        i - 3] == 'from':  # from 300 to Quantity0(900 meters) -> Quantity0
                        Quantity[int(w[9])] = ' '.join(cur_words[i - 3:i]) + ' ' + Quantity[int(w[9])]
                        sentence = sentence.replace(' '.join(cur_words[i - 3:i]) + ' ' + w, w)
                        enti_dict['quantity'] = Quantity
                    elif cur_words[i - 1] == 'and' and cur_words[i - 2].isnumeric() and cur_words[
                        i - 3] == 'between':  # between 700 and Quantity0(2000 meters) -> Quantity0
                        Quantity[int(w[9])] = ' '.join(cur_words[i - 3:i]) + ' ' + Quantity[int(w[9])]
                        sentence = sentence.replace(' '.join(cur_words[i - 3:i]) + ' ' + w, w)
                        enti_dict['quantity'] = Quantity
                    elif cur_words[i + 1] == 'per' and cur_words[i + 2] == 'second':
                        Quantity[int(w[9])] = Quantity[int(w[9])] + ' ' + ' '.join(cur_words[i + 1:i + 3])
                    else:
                        enti_dict['quantity'] = Quantity
        if not len(Percent) == 0:
            enti_dict['percent'] = Percent
        if not len(Date) == 0:
            for w in cur_words:
                if w.startswith('EDate'):
                    i = cur_words.index(w)
                    if cur_words[i - 2].isnumeric() and cur_words[i - 1] == 'to':  # from 2000 to Date0 -> Date0
                        Date[int(w[5])] = ' '.join(cur_words[i - 3:i]) + ' ' + Date[int(w[5])]
                        sentence = sentence.replace(' '.join(cur_words[i - 3:i]) + ' ' + w, w)
                        enti_dict['date'] = Date
                    elif i + 2 < len(cur_words) and cur_words[i + 2].isnumeric() and cur_words[
                        i + 1] == 'to':  # from Date0 to 1994
                        Date[int(w[5])] = cur_words[i - 1] + ' ' + Date[int(w[5])] + ' ' + ' '.join(cur_words[i + 1:i + 3])
                        sentence = sentence.replace(cur_words[i - 1] + ' ' + w + ' ' + ' '.join(cur_words[i + 1:i + 3]), w)
                        enti_dict['date'] = Date
                    elif cur_words[i - 1] == 'from' and i + 1 == len(cur_words):  # from Date0 (1997 to 2004)
                        Date[int(w[5])] = 'from ' + Date[int(w[5])]
                        sentence = sentence.replace('from ' + w, w)
                        enti_dict['date'] = Date
                    elif cur_words[i - 1] == 'from' and i + 1 < len(cur_words) and not cur_words[
                                                                                           i + 1] == 'to':  # from Date0 (1997 to 2004) in Utrecht
                        Date[int(w[5])] = 'from ' + Date[int(w[5])]
                        sentence = sentence.replace('from ' + w, w)
                        enti_dict['date'] = Date
                    elif cur_words[i - 1] == 'from' and cur_words[i + 1] == 'to' and cur_words[i + 2].startswith(
                            'Date') and i + 2 < len(cur_words):  # from date0 to date1 -> date0
                        Date[int(w[5])] = 'from ' + Date[int(w[5])] + ' to ' + Date[int(cur_words[i + 2][5])]
                        Date.remove(Date[int(cur_words[i + 2][5])])
                        sentence = sentence.replace('from ' + w + ' to ' + cur_words[i + 2], w)
                        enti_dict['date'] = Date
                    elif cur_words[i - 1] == 'over':  # over 65 years
                        Date[int(w[5])] = 'over ' + Date[int(w[5])]
                        sentence = sentence.replace('over ' + w, w)
                        enti_dict['date'] = Date
                    else:
                        enti_dict['date'] = Date

        return enti_dict, sentence


    # [X] Clean noun_phrases after noun chunks recognition, remove superlatives and comparatives, placenames, entities...
    def noun_phrases_correct(self, noun_phrases_list):
        noun_phrases_CleanList = []

        for cur_noun in noun_phrases_list:
            if 'each' in cur_noun:
                cur_noun = cur_noun.replace('each ', '')
            if cur_noun in cn:
                noun_phrases_CleanList.append(cur_noun)
            else:
                cur_p = nt.sent_tokenize(cur_noun)
                tokenized_sen = [nt.word_tokenize(p) for p in cur_p]  # [['nearest', 'supermarket']]
                if (any('area' in m for m in tokenized_sen[0]) and not any('equantity' in n for n in tokenized_sen[0])) or not any('area' in m for m in tokenized_sen[0]): # remove 'equantity0 area of road'
                    cur_pos = [nltk.pos_tag(cur_sen) for cur_sen in tokenized_sen][
                        0]  # [('nearest', 'JJS'), ('supermarket', 'NN')]
                    for e in cur_pos:
                        pos.append(e)
                    res = [sub[0] for sub in cur_pos if
                           ('JJS' in sub[1] and not sub[0] == 'west') or 'JJR' in sub[1] or 'RBS' in sub[1] or 'RBR' in sub[
                               1]]  # ['longest', 'more', 'most']

                    if 'most' in res or 'more' in res:  # most intense, also remove intense; more than, also remove than
                        mostIndex = [cur_pos.index(sub) for sub in cur_pos if sub[0] == 'most' or sub[0] == 'more']
                        nextIndex = mostIndex[0] + 1
                        if cur_pos[nextIndex][1] == 'JJ' or cur_pos[nextIndex][0] == 'than':
                            res.append(cur_pos[nextIndex][0])

                    nounStr_Clean = [ele for ele in tokenized_sen[0] if ele not in res and ele.lower() not in removeWords
                                     and not ele.startswith('placename') and not ele.startswith('edate') and not
                                     ele.startswith('equantity') and not ele.startswith('etime') and not ele.startswith(
                        'epercent')
                                     and not ele.startswith(
                        'outside') and not ele.isnumeric() and not ele == ',' or ele == '911']

                    cur_noun_Clean = ' '.join(text for text in nounStr_Clean).strip()

                    # [X] remove 'areas' in 'what areas', 'many' in 'how many'...'how many buildings'->'buildings'
                    if cur_noun_Clean.startswith('areas'):
                        cur_noun_Clean = cur_noun_Clean.replace('areas', '')
                    if cur_noun_Clean.startswith('many'):
                        cur_noun_Clean = cur_noun_Clean.replace('many', '')
                    if cur_noun_Clean.startswith('much'):
                        cur_noun_Clean = cur_noun_Clean.replace('much', '')

                    if cur_noun_Clean:
                        noun_phrases_CleanList.append(cur_noun_Clean.strip())

        return noun_phrases_CleanList


    # [X] Identify Core concepts: field, object, event, network, contentAmount, coverageAmount, conProportion, proportion
    # input string sentence: What is number of crime cases for each police district in PlaceName0 in Date0
    # output string sentence: what is conamount0 era of event0 for each object0 in placename0 in date0
    # output tuple: {'Object': ['police district'], 'Event': ['crime cases'], 'ConAmount': ['number']}
    def core_concept_match(self, sentence):
        cur_sen = sentence
        cur_doc = nlp(cur_sen)
        cur_matches = matcher(cur_doc)
        match_phrases = [cur_doc[start: end].text for mat_id, start, end in cur_matches]
        for cur_ph in match_phrases:
            cur_sen = cur_sen.replace(cur_ph + ' ', '')
        cur_doc2 = nlp(cur_sen)
        noun_list = [noun.text for noun in cur_doc2.noun_chunks]
        if not len(match_phrases) == 0:
            for cur_phr in match_phrases:
                noun_list.append(cur_phr)

        noun_list_Clean = self.noun_phrases_correct(noun_list)

        # [X] Identify core concepts from noun chunks
        coreConcept_dect = {}
        field = []
        object = []
        objectQuality = []
        event = []
        eventQuality = []
        network = []
        networkQuality = []
        quality = []
        conAmount = []
        objConAmount = []
        eveConAmount = []
        covAmount = []
        conConPro = []
        objConobjConPro = []
        eveConobjConPro = []
        conCovPro = []
        objConobjCovPro = []
        eveConobjCovPro = []
        covPro = []
        proportion = []

        fie_loc = 0
        obj_loc = 0
        objQ_loc = 0
        eve_loc = 0
        eveQ_loc = 0
        net_loc = 0
        netQ_loc = 0
        qua_loc = 0
        conA_loc = 0
        objConA_loc = 0
        eveConA_loc = 0
        covA_loc = 0
        objConobjConP_loc = 0
        eveconobjconP_loc = 0
        conconP_loc = 0
        objConobjCovP_loc = 0
        eveConobjCovP_loc = 0
        concovP_loc = 0
        covpro_loc = 0
        pro_loc = 0

        for cur_noun in noun_list_Clean:
            cur_w = cur_noun.split(' ')
            # print('cur_w:', cur_w)
            if cur_noun in coreCon_dict['text'] and not cur_noun == 'population':
                cur_index = coreCon_dict['text'].index(cur_noun)
                if coreCon_dict['tag'][cur_index] == 'field':
                    field.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'field' + str(fie_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    fie_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'object':
                    object.append(cur_noun)
                    sentence = sentence.replace(cur_noun, 'object' + str(obj_loc))
                    obj_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'object quality':
                    objectQuality.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'objectquality' + str(objQ_loc) + ' ' +
                                                coreCon_dict['measureLevel'][
                                                    cur_index])
                    objQ_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'event':
                    event.append(cur_noun)
                    sentence = sentence.replace(cur_noun, 'event' + str(eve_loc))
                    eve_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'event quality':
                    eventQuality.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'eventquality' + str(eveQ_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    eveQ_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'network':
                    cur_ns = cur_noun.split(' ')[0]
                    cur_i = [x for x, y in enumerate(pos) if y[0] == cur_ns]
                    if len(cur_i) >= 1 and (pos[cur_i[0] - 1][1] == 'JJS' or pos[cur_i[0] - 1][1] == 'RBS'):
                        cur_np = pos[cur_i[0] - 1][0] + ' ' + cur_noun
                        network.append(cur_np)
                        sentence = sentence.lower().replace(cur_np, 'network' + str(net_loc))
                        net_loc += 1
                    else:
                        network.append(cur_noun)
                        sentence = sentence.lower().replace(cur_noun, 'network' + str(net_loc))
                        net_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'network quality':
                    networkQuality.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'networkquality' + str(eveQ_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    netQ_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'quality':
                    quality.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'quality' + str(qua_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    qua_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'covamount':
                    covAmount.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'covamount' + str(covA_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    covA_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'conamount':
                    conAmount.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'conamount' + str(conA_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    conA_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'object conamount':
                    objConAmount.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'objconamount' + str(objConA_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    objConA_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'event conamount':
                    eveConAmount.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'eveconamount' + str(eveConA_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    eveConA_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'objconobjconpro':
                    objConobjConPro.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'objconobjconpro' + str(conconP_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    objConobjConP_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'eveconobjconpro':
                    eveConobjConPro.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'eveconobjconpro' + str(conconP_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    eveconobjconP_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'conconpro':
                    conConPro.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'conconpro' + str(conconP_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    conconP_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'objconobjcovpro':
                    objConobjCovPro.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'objconobjcovpro' + str(concovP_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    objConobjCovP_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'eveconobjcovpro':
                    eveConobjCovPro.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'eveconobjcovpro' + str(concovP_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    eveConobjCovP_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'concovpro':
                    conCovPro.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'concovpro' + str(concovP_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    concovP_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'covpro':
                    covPro.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'covpro' + str(covpro_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    covpro_loc += 1
                elif coreCon_dict['tag'][cur_index] == 'proportion':
                    proportion.append(cur_noun)
                    sentence = sentence.replace(cur_noun,
                                                'proportion' + str(pro_loc) + ' ' + coreCon_dict['measureLevel'][
                                                    cur_index])
                    pro_loc += 1
            elif cur_w[0] == 'average' or cur_w[0] == 'median' or cur_w[0] == 'total':  # average Euclidean distance
                cur_r = ' '.join(cur_w[1:])  # 'Euclidean' 'distance' -> 'Euclidean distance'
                if cur_r in coreCon_dict['text']:
                    cur_in = coreCon_dict['text'].index(cur_r)
                    if coreCon_dict['tag'][cur_in] == 'field':
                        field.append(cur_r)
                        sentence = sentence.replace(cur_r,
                                                    'field' + str(fie_loc) + ' ' + coreCon_dict['measureLevel'][cur_in])
                        fie_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'object':
                        object.append(cur_r)
                        sentence = sentence.replace(cur_r, 'object' + str(obj_loc))
                        obj_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'object quality':
                        objectQuality.append(cur_r)
                        sentence = sentence.replace(cur_r,
                                                    'objectquality' + str(objQ_loc) + ' ' + coreCon_dict['measureLevel'][
                                                        cur_in])
                        objQ_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'event':
                        event.append(cur_r)
                        sentence = sentence.replace(cur_r, 'event' + str(eve_loc))
                        eve_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'event quality':
                        eventQuality.append(cur_r)
                        sentence = sentence.replace(cur_r,
                                                    'eventquality' + str(eveQ_loc) + ' ' + coreCon_dict['measureLevel'][
                                                        cur_in])
                        eveQ_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'network':
                        network.append(cur_r)
                        sentence = sentence.lower().replace(cur_r, 'network' + str(net_loc))
                        net_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'network quality':
                        networkQuality.append(cur_r)
                        sentence = sentence.lower().replace(cur_r, 'networkquality' + str(netQ_loc) + ' ' + coreCon_dict['measureLevel'][
                                                        cur_in])
                        netQ_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'quality':
                        quality.append(cur_r)
                        sentence = sentence.replace(cur_r,
                                                    'quality' + str(qua_loc) + ' ' + coreCon_dict['measureLevel'][cur_in])
                        qua_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'covamount':
                        covAmount.append(cur_r)
                        sentence = sentence.replace(cur_r, 'covamount' + str(covA_loc) + ' ' + coreCon_dict['measureLevel'][
                            cur_in])
                        covA_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'conamount':
                        conAmount.append(cur_r)
                        sentence = sentence.replace(cur_r, 'conamount' + str(conA_loc) + ' ' + coreCon_dict['measureLevel'][
                            cur_in])
                        conA_loc += 1
                    elif coreCon_dict['tag'][cur_in] == 'object conamount':
                        objConAmount.append(cur_r)
                        sentence = sentence.replace(cur_r,
                                                    'objconamount' + str(objConA_loc) + ' ' + coreCon_dict['measureLevel'][
                                                        cur_in])
                        objConA_loc += 1

        if 'population' in sentence:
            objConAmount.append('population')
            sentence = sentence.replace('population', 'objconamount' + str(objConA_loc) + ' ' + 'era')
            objConA_loc += 1

        # [X] 'local road' is network in 'What is the potential accessibility by local road for each 2 by 2 km grid cell
        # in Finland'; 'roads' is object in 'Which roads are intersected with forest areas in UK'
        for cur_noun in noun_list_Clean:
            if cur_noun in networkSet:
                if 'network' in sentence or 'access' in cur_sen or 'connectivity' in cur_sen:
                    network.append(cur_noun)
                    sentence = sentence.lower().replace(cur_noun, 'network' + str(net_loc))
                    net_loc += 1
                else:
                    object.append(cur_noun)
                    sentence = sentence.replace(cur_noun, 'object' + str(obj_loc))
                    obj_loc += 1


        if not field == []:
            coreConcept_dect['field'] = field
        if not object == []:
            coreConcept_dect['object'] = object
        if not objectQuality == []:
            coreConcept_dect['objectquality'] = objectQuality
        if not event == []:
            coreConcept_dect['event'] = event
        if not eventQuality == []:
            coreConcept_dect['eventquality'] = eventQuality
        if not network == []:
            coreConcept_dect['network'] = network
        if not networkQuality == []:
            coreConcept_dect['networkquality'] = networkQuality
        if not quality == []:
            coreConcept_dect['quality'] = quality
        if not conAmount == []:
            coreConcept_dect['conamount'] = conAmount
        if not len(objConAmount) == 0:
            coreConcept_dect['objconamount'] = objConAmount
        if not len(eveConAmount) == 0:
            coreConcept_dect['eveconamount'] = eveConAmount
        if not covAmount == []:
            coreConcept_dect['covamount'] = covAmount
        if not conConPro == []:
            coreConcept_dect['conconpro'] = conConPro
        if not objConobjConPro == []:
            coreConcept_dect['objconobjconpro'] = objConobjConPro
        if not eveConobjConPro == []:
            coreConcept_dect['eveconobjconpro'] = eveConobjConPro
        if not conCovPro == []:
            coreConcept_dect['concovpro'] = conCovPro
        if not objConobjCovPro == []:
            coreConcept_dect['objconobjcovpro'] = objConobjCovPro
        if not eveConobjCovPro == []:
            coreConcept_dect['eveconobjcovpro'] = eveConobjCovPro
        if not covPro == []:
            coreConcept_dect['covpro'] = covPro
        if not proportion == []:
            coreConcept_dect['proportion'] = proportion

        return coreConcept_dect, sentence.lower()


    # [X] Extract parser rules(tags) and text from parserTreeString
    def get_text(self, cur_treeStr):
        nodetextDic = {}
        root = BracketMatch(cur_treeStr)
        cur_match = root
        for i in range(len(cur_treeStr)):
            if '(' == cur_treeStr[i]:
                new_match = BracketMatch(cur_treeStr, cur_match, i)
                cur_match.nested_matches.append(new_match)
                cur_match = new_match
            elif ')' == cur_treeStr[i]:
                cur_match.end = i
                cur_match = cur_match.parent
            else:
                continue
        nodes_list = root.nested_matches
        tag = []
        while nodes_list != []:
            node = nodes_list.pop(0)
            nodes_list.extend(node.nested_matches)
            nodeStr = str(node).strip()
            nodetextDic.setdefault('tag', []).append(nodeStr.split()[0])
            nodetextDic.setdefault('text', []).append(' '.join(nodeStr.split()[1:][0:len(nodeStr.split()[1:])]))

        return nodetextDic


    # [X]Extract core concept from texts and tags of the parse tree
    # Input: {'tag': ['condition', 'boolR', 'extremaR', 'coreC', 'coreC', 'coreC'], 'text': ['of to', 'has', 'highest',
    # 'proportion 0 ira', 'object 1', 'objconamount 0 count']}
    # Output: {'tag': ['coreC', 'coreC', 'coreC'], 'text': ['proportion 0 ira', 'object 1', 'objconamount 0 count']}
    def core_concept_extract(self, TreeDict):
        cur_TD = {}
        keep_set = {'coreC', 'networkC', 'networkQ', 'location', 'allocation', 'conAm', 'boolField', 'distField', 'serviceObj', 'aggre',
                    'compareR'}  # 'extremaR',
        tag_in = [i for i, x in enumerate(TreeDict['tag']) if not x in keep_set]
        cur_TD['tag'] = [TreeDict['tag'][i] for i in range(0, len(TreeDict['tag'])) if i not in tag_in]
        for i in range(0, len(cur_TD['tag'])):
            if cur_TD['tag'][i] == 'boolField' or cur_TD['tag'][i] == 'distField' or cur_TD['tag'][i] == 'serviceObj':
                cur_TD['tag'][i] = cur_TD['tag'][i].lower()
        cur_TD['text'] = [TreeDict['text'][i] for i in range(0, len(TreeDict['text'])) if i not in tag_in]

        # at least 3000 meters from the rivers or Where are the luxury hotels with more than 20 bedrooms
        if 'compareR' in cur_TD['tag'] and ('boolfield' in cur_TD['tag'] or (len(cur_TD['tag']) == 2 and cur_TD['tag'].index('compareR')+1 < 2 and cur_TD['tag'][cur_TD['tag'].index('compareR')+1] == 'coreC')):
            compR_index = cur_TD['tag'].index('compareR')
            cur_TD['tag'].pop(compR_index)
            cur_TD['text'].pop(compR_index)

        # from origin to the nearest destination, add extreDist(nearest) to cur_TD
        if 'extreDist' in TreeDict['tag'] and (
                    'networkC' in TreeDict['tag'] or 'networkQ' in TreeDict['tag']) and 'serviceObj' not in TreeDict['tag']:
            cur_in = [cur_TD['tag'].index(i) for i in TreeDict['tag'] if i.startswith('network')][0]
            cur_TD['tag'].insert(cur_in, 'extreDist')
            cur_TD['text'].insert(cur_in, TreeDict['text'][TreeDict['tag'].index('extreDist')])

        return cur_TD


    # [X]Write core concepts in the questions into the designed structure
    # Input dictionary: {'tag': ['origin', 'destination', 'networkC', 'serviceObj', 'boolField'],
    # 'text': [['object 1', 'hexagonal grids with diameter of 2000 meters'], 'object 0', 'network 0', 'from to', '']}
    # Output[0]: [{'type': ['object'], 'id': '0', 'keyword': 'centroid'}, {...}, ...]
    # Output[1]:{'tag': ['origin', 'destination', 'networkC', 'serviceObj', 'boolField'],
    # 'text': [['object 1', 'hexagonal grids with diameter of equantity 1'], 'object 0', 'network 0', 'from to', ''],
    # 'id': [['0', '1'], '2', '3', '4']}
    def write_type(self, coreDict):  # , core_index
        corety = []
        csign = 0

        gen_coreC = {'distfield', 'serviceobj', 'boolfield'}

        for cur_tag in coreDict['tag']:
            if cur_tag in gen_coreC or cur_tag == 'location' or cur_tag == 'allocation':
                coreType = {}
                coreType['type'] = cur_tag
                coreType['id'] = str(self.core_id)
                coreType['keyword'] = ''
                corety.append(coreType)
                coreDict.setdefault('id', []).append(str(self.core_id))
                self.core_id += 1
            elif cur_tag == 'conAm':
                coreType = {}
                coreType['type'] = 'conamount'
                coreType['id'] = str(self.core_id)
                coreType['keyword'] = ''
                corety.append(coreType)
                coreDict.setdefault('id', []).append(str(self.core_id))
                self.core_id += 1
            elif cur_tag == 'grid' or cur_tag == 'distanceBand':
                coreType = {}
                coreType['type'] = cur_tag
                coreType['id'] = str(self.core_id)
                coreType['keyword'] = coreDict['text'][coreDict['tag'].index(cur_tag)]
                corety.append(coreType)
                coreDict.setdefault('id', []).append(str(self.core_id))
                self.core_id += 1
            elif cur_tag == 'aggre':
                coreType = {}
                coreType['type'] = cur_tag
                coreType['id'] = str(self.core_id)
                curtag_index = coreDict['tag'].index(cur_tag)
                coreType['keyword'] = coreDict['text'][curtag_index]
                if coreDict['tag'][curtag_index-1] == 'extreDist' and coreDict['text'][curtag_index-2].split(' ')[-1] in measLevel:
                    coreType['measureLevel'] = coreDict['text'][curtag_index-2].split(' ')[-1]
                elif coreDict['text'][curtag_index-1].split(' ')[-1] in measLevel:
                    coreType['measureLevel'] = coreDict['text'][curtag_index - 1].split(' ')[-1]
                corety.append(coreType)
                coreDict.setdefault('id', []).append(str(self.core_id))
                self.core_id += 1
            elif cur_tag == 'networkC':
                # read network keywords
                coreType = {}
                nts = coreDict['text'][coreDict['tag'].index('networkC')].split(' ')
                coreType['type'] = nts[0]
                coreType['id'] = str(self.core_id)
                coreType['keyword'] = self.result[nts[0]][int(nts[1])]  # e.g., driving time, network distance
                corety.append(coreType)
                coreDict.setdefault('id', []).append(str(self.core_id))
                self.core_id += 1
            elif cur_tag == 'networkQ':
                coreType = {}
                nts = coreDict['text'][coreDict['tag'].index('networkQ')].split(' ')
                coreType['type'] = nts[0]
                coreType['id'] = str(self.core_id)
                coreType['keyword'] = self.result[nts[0]][int(nts[1])]  # e.g., driving time, network distance
                coreType['measureLevel'] = nts[2]
                corety.append(coreType)
                coreDict.setdefault('id', []).append(str(self.core_id))
                self.core_id += 1
            elif cur_tag == 'coreC':
                if csign == 1:
                    continue
                else:
                    clocs = [x for x, y in enumerate(coreDict['tag']) if y == cur_tag]
                    for cloc in clocs:
                        coreType = {}
                        cts = coreDict['text'][cloc].split(' ')
                        if len(cts) == 2:  # object 0
                            coreType['type'] = cts[0]
                            coreType['id'] = str(self.core_id)
                            coreType['keyword'] = self.result[cts[0]][int(cts[1])]
                            corety.append(coreType)
                            coreDict.setdefault('id', []).append(str(self.core_id))
                            self.core_id += 1
                        elif len(cts) == 3:  # # eveconobjconpro 0 ira
                            coreType['type'] = cts[0]
                            coreType['id'] = str(self.core_id)
                            coreType['keyword'] = self.result[cts[0]][int(cts[1])]
                            coreType['measureLevel'] = cts[2]
                            corety.append(coreType)
                            coreDict.setdefault('id', []).append(str(self.core_id))
                            self.core_id += 1
                    csign += 1
            elif cur_tag == 'destination':
                des_id = []
                for d in coreDict['text'][coreDict['tag'].index(cur_tag)]:
                    coreType = {}
                    dtext = d.split(' ')
                    coreType['type'] = dtext[0]
                    coreType['id'] = str(self.core_id)
                    coreType['keyword'] = self.result[dtext[0]][int(dtext[1])]
                    corety.append(coreType)
                    des_id.append(str(self.core_id))
                    self.core_id += 1
                coreDict.setdefault('id', []).append(des_id)
            elif cur_tag == 'origin':
                ori_id = []
                for o in coreDict['text'][coreDict['tag'].index(cur_tag)]:
                    coreType = {}
                    if 'grid' in o:
                        coreType['type'] = 'grid'
                        coreType['id'] = str(self.core_id)
                        coreType['keyword'] = o
                        corety.append(coreType)
                        ori_id.append(str(self.core_id))
                        self.core_id += 1
                    else:
                        otext = o.split(' ')
                        coreType['type'] = otext[0]
                        coreType['id'] = str(self.core_id)
                        coreType['keyword'] = self.result[otext[0]][int(otext[1])]
                        corety.append(coreType)
                        ori_id.append(str(self.core_id))
                        self.core_id += 1
                coreDict.setdefault('id', []).append(ori_id)
            elif cur_tag == 'extent':
                coreType = {}
                coreType['type'] = 'object'
                coreType['id'] = str(self.core_id)
                coreType['keyword'] = self.result['placename'][int(coreDict['text'][0].split(' ')[1])]
                corety.append(coreType)
                coreDict.setdefault('id', []).append(str(self.core_id))
                self.core_id += 1

        return corety, coreDict


    # [X] Generate parser tree of question by the GeoAnQu grammar and extract core concept transformations
    def geo_parser(self, sentence):
        ques_incorrect = ''

        coreTypes = {}
        wei_len = 0

        input = InputStream(sentence)  # [X]sentence =  'What areas are with slope larger than 10 in Spain'
        lexer = GeoAnQuLexer(input)  # get lexer rule
        stream = CommonTokenStream(lexer)  # token stream to tokens
        parser = GeoAnQuParser(stream)
        try:
            tree = parser.start()  # [X] get parsed tree of the sentence
            treeStr = Trees.toStringTree(tree, None, parser)  # Print out a whole tree in LISP form
            quesTextDic = self.get_text(treeStr)

            sequence = [ele for ele in quesTextDic['tag'] if ele in que_stru]
            sequence.reverse()

            if 'condition' in sequence:
                conCores = []
                con_count = treeStr.count('condition')
                for cur_i in range(0, con_count):
                    con_treeStr = Trees.toStringTree(tree.condition(cur_i), None, parser)
                    conTextDic = self.get_text(con_treeStr)
                    conCore = self.core_concept_extract(conTextDic)
                    if 'destination' in conTextDic['tag']:
                        des_list = []
                        if 'serviceObj' in conTextDic['tag']:
                            destination = tree.condition(cur_i).boolField().serviceObj().destination()
                            dest_childCount = destination.getChildCount()
                        elif 'distField' in conTextDic['tag']:
                            destination = tree.condition(cur_i).boolField().distField().destination(0)
                            dest_childCount = destination.getChildCount()
                        else:
                            destination = tree.condition(cur_i).destination()
                            dest_childCount = destination.getChildCount()
                        for d_i in range(0, dest_childCount):
                            dest_text = destination.getChild(d_i).getText()
                            if 'object' in dest_text or 'event' in dest_text:
                                dest_text = dest_text[:-1] + ' ' + dest_text[-1]
                                des_list.append(dest_text)
                            elif 'placename' in dest_text:
                                dest_text = dest_text[:-1] + ' ' + dest_text[-1]
                                des_list.append(dest_text)
                        des_list.reverse()
                        conCore['tag'].append('destination')
                        conCore['text'].append(des_list)
                    if 'origin' in conTextDic['tag']:  # 'centriods of object/grid' or 'object' or 'grid'
                        ori_list = []
                        if 'serviceObj' in conTextDic['tag']:
                            origin = tree.condition(cur_i).boolField().serviceObj().origin()
                            ori_childCount = origin.getChildCount()
                        elif 'distField' in conTextDic['tag']:
                            origin = tree.condition(cur_i).boolField().distField().origin(0)
                            ori_childCount = origin.getChildCount()
                        else:
                            origin = tree.condition(cur_i).origin()
                            ori_childCount = origin.getChildCount()
                        for o_i in range(0, ori_childCount):
                            ori_text = origin.getChild(o_i).getText()
                            if 'object' in ori_text or 'event' in ori_text:
                                ori_text = ori_text[:-1] + ' ' + ori_text[-1]
                                ori_list.append(ori_text)
                            elif 'grid' in ori_text:
                                if 'equantity' in ori_text:
                                    ein = ori_text.index('equantity') + 9
                                    ori_text = ori_text.replace('equantity' + ori_text[ein],
                                                                self.result['quantity'][int(ori_text[ein])] + ' ')
                                if 'of' in ori_text:
                                    ori_text = ori_text.replace('of', 'of ')
                                if 'with' in ori_text:
                                    ori_text = ori_text.replace('with', ' with ')
                                ori_list.append(ori_text.strip())
                                # ori_list in forward order, e.g, [object0, grid], object = centroid
                            elif 'placename' in ori_text:
                                ori_text = ori_text[:-1] + ' ' + ori_text[-1]
                                ori_list.append(ori_text.strip())
                            ori_list.reverse()
                            conCore['tag'].append('origin')
                            conCore['text'].append(ori_list)
                    if 'grid' in conTextDic['tag'] and 'origin' not in conTextDic['tag'] and 'destination' not in \
                            conTextDic['tag']:
                        cgrid_text = tree.condition(cur_i).grid().getText()
                        if 'equantity' in cgrid_text:
                            ein = cgrid_text.index('equantity') + 9
                            cgrid_text = cgrid_text.replace('equantity' + cgrid_text[ein],
                                                            self.result['quantity'][int(cgrid_text[ein])] + ' ')
                        conCore['tag'].append('grid')
                        conCore['text'].append(cgrid_text)
                    conCore['tag'].reverse()
                    conCore['text'].reverse()
                    conCores.insert(0, conCore)

            if 'measure' in sequence:
                mea_treeStr = Trees.toStringTree(tree.measure(), None, parser)
                meaTextDic = self.get_text(mea_treeStr)
                meaCore = self.core_concept_extract(meaTextDic)
                if 'destination' in meaTextDic['tag']:
                    destination = tree.measure().destination(0)
                    dest_childCount = destination.getChildCount()  # 'closest object0', childcount = 2
                    des_list = []
                    for d_i in range(0, dest_childCount):
                        dest_text = destination.getChild(d_i).getText()
                        if 'object' in dest_text or 'event' in dest_text:
                            dest_text = dest_text[:-1] + ' ' + dest_text[-1]
                            des_list.append(dest_text)
                        elif 'placename' in dest_text:
                            dest_text = dest_text[:-1] + ' ' + dest_text[-1]
                            des_list.append(dest_text.strip())
                    des_list.reverse()
                    meaCore['tag'].append('destination')
                    meaCore['text'].append(des_list)
                if 'origin' in meaTextDic['tag']:  # 'centriods of object/grid' or 'object' or 'grid'
                    origin = tree.measure().origin(0)
                    ori_childCount = origin.getChildCount()
                    ori_list = []
                    for o_i in range(0, ori_childCount):
                        ori_text = origin.getChild(o_i).getText()
                        if 'object' in ori_text or 'event' in ori_text:
                            ori_text = ori_text[:-1] + ' ' + ori_text[-1]
                            ori_list.append(ori_text)
                        elif 'grid' in ori_text:
                            if 'equantity' in ori_text:
                                ein = ori_text.index('equantity') + 9
                                ori_text = ori_text.replace('equantity' + ori_text[ein],
                                                            self.result['quantity'][int(ori_text[ein])] + ' ')
                            if 'of' in ori_text:
                                ori_text = ori_text.replace('of', 'of ')
                            if 'with' in ori_text:
                                ori_text = ori_text.replace('with', ' with ')
                            ori_list.append(ori_text.strip())
                            # ori_list in forward order, e.g, [object0, grid], object = centroid
                        elif 'placename' in ori_text:
                            ori_text = ori_text[:-1] + ' ' + ori_text[-1]
                            ori_list.append(ori_text.strip())
                    ori_list.reverse()
                    meaCore['tag'].append('origin')
                    meaCore['text'].append(ori_list)
                meaCore['tag'].reverse()
                meaCore['text'].reverse()
                if 'weight' in meaTextDic['tag']:
                    wei_loc = meaTextDic['tag'].index('weight')
                    wei_len = len(meaTextDic['tag']) - wei_loc - 1

            if 'measure1' in sequence:
                mea1_treeStr = Trees.toStringTree(tree.measure1(), None, parser)
                mea1TreeDic = self.get_text(mea1_treeStr)
                mea1Core = self.core_concept_extract(mea1TreeDic)

            if 'subcon' in sequence:
                subcon_treeStr = Trees.toStringTree(tree.subcon(), None, parser)
                subconTextDic = self.get_text(subcon_treeStr)
                subconCore = self.core_concept_extract(subconTextDic)
                subconCore['tag'].reverse()
                subconCore['text'].reverse()

            if 'support' in sequence:
                sup_treeStr = Trees.toStringTree(tree.support(), None, parser)
                supTextDic = self.get_text(sup_treeStr)
                supCore = self.core_concept_extract(supTextDic)
                if 'grid' in supTextDic['tag']:
                    grid_text = tree.support().grid().getText()
                    if 'equantity' in grid_text:
                        ein = grid_text.index('equantity') + 9
                        grid_text = grid_text.replace('equantity' + grid_text[ein],
                                                      self.result['quantity'][int(grid_text[ein])] + ' ')
                    supCore['tag'].append('grid')
                    supCore['text'].append(grid_text)
                if 'distBand' in supTextDic['tag']:
                    distBand_text = tree.support().distBand().getText()
                    if 'equantity' in distBand_text:
                        eins = [m.start() for m in re.finditer('equantity', distBand_text)]
                        e = 9
                        for ein in eins:
                            distBand_text = distBand_text.replace('equantity' + distBand_text[ein + e],
                                                                  ' equantity ' + distBand_text[ein + e] + ' ')
                            e = e + 3
                        dBts = distBand_text.split(' ')
                        eqins = [x for x, y in enumerate(dBts) if y == 'equantity']
                        qlocs = []
                        for eqin in eqins:
                            qlocs.append(dBts[eqin + 1])
                        for qloc in qlocs:
                            distBand_text = distBand_text.replace(
                                'equantity ' + distBand_text[distBand_text.index('equantity') + 10],
                                self.result['quantity'][int(qloc)])
                    supCore['tag'].append('distanceBand')
                    supCore['text'].append(distBand_text.strip())
                supCore['tag'].reverse()
                supCore['text'].reverse()

            for seq in sequence:
                if seq == 'measure':
                    meaTypes = self.write_type(meaCore)
                    self.coreConTrans.setdefault('types', []).extend(meaTypes[0])  # type info in the final results
                    coreTypes.setdefault('funcRole', []).append(seq)
                    coreTypes.setdefault('types', []).append(meaTypes[1])
                    if wei_len:
                        coreTypes['weight'] = wei_len
                elif seq == 'measure1':
                    mea1Types = self.write_type(mea1Core)
                    self.coreConTrans.setdefault('types', []).extend(mea1Types[0])
                    coreTypes.setdefault('funcRole', []).append(seq)
                    coreTypes.setdefault('types', []).append(mea1Types[1])
                elif seq == 'condition':
                    conTypes = self.write_type(conCores[0])
                    self.coreConTrans.setdefault('types', []).extend(conTypes[0])
                    coreTypes.setdefault('funcRole', []).append(seq)
                    coreTypes.setdefault('types', []).append(conTypes[1])
                    conCores.pop(0)
                elif seq == 'subcon':
                    subconTypes = self.write_type(subconCore)
                    self.coreConTrans.setdefault('types', []).extend(subconTypes[0])
                    coreTypes.setdefault('funcRole', []).append(seq)
                    coreTypes.setdefault('types', []).append(subconTypes[1])
                elif seq == 'support':
                    supTypes = self.write_type(supCore)
                    self.coreConTrans.setdefault('types', []).extend(supTypes[0])
                    coreTypes.setdefault('funcRole', []).append(seq)
                    coreTypes.setdefault('types', []).append(supTypes[1])

            ext_count = treeStr.count('extent')
            if ext_count:
                for cur_i in range(0, ext_count):
                    ext_treeStr = Trees.toStringTree(tree.extent()[cur_i], None, parser)
                    extTextDic = self.get_text(ext_treeStr)
                    extTypes = self.write_type(extTextDic)
                    self.coreConTrans.setdefault('types', []).extend(extTypes[0])
                    self.coreConTrans.setdefault('extent', []).append(extTypes[1]['id'][0])
                coreTypes.setdefault('funcRole', []).append('extent')
                coreTypes.setdefault('types', []).append(extTypes[1]['id'])

            tem_count = treeStr.count('temEx')
            if tem_count:
                for cur_t in range(0, tem_count):
                    tem_treeStr = Trees.toStringTree(tree.temEx(cur_t), None, parser)
                    temTextDic = self.get_text(tem_treeStr)
                    temsp = temTextDic['text'][0].split(' ')
                    self.coreConTrans.setdefault('temporalEx', []).append(self.result['date'][int(temsp[1])])
                coreTypes.setdefault('funcRole', []).append('temEx')
                coreTypes.setdefault('types', []).append(self.coreConTrans['temporalEx'])


        except Exception as e:
            # [SC][TODO] error logging
            print("============================ Exception in geo_parser:")
            print(e)
            ques_incorrect = sentence

        return treeStr, coreTypes, ques_incorrect


    # [X] Generate core concept transformations within condition, measure...
    # Input TypeDict = {'tag': ['coreC', 'distField', 'boolField'], 'text': ['object 1', 'from', ''], 'id': ['1', '2', '3']}
    # Output [{'before': ['1'], 'after': ['2']}, {'before': ['2'], 'after': ['3']}]
    def write_trans_within(self, TypeDict):
        transwithin = []
        coreC_sign = 0

        for tt in TypeDict['tag']:
            if tt == 'boolfield' or tt == 'allocation' or tt == 'conAm':
                if TypeDict['tag'].index(tt) - 1 >= 0:
                    trans = {}
                    trans['before'] = [TypeDict['id'][TypeDict['tag'].index(tt) - 1]]
                    trans['after'] = [TypeDict['id'][TypeDict['tag'].index(tt)]]
                    transwithin.append(trans)
            elif tt == 'distfield':
                if TypeDict['tag'].index(tt) - 1 >= 0:
                    cur_tag = TypeDict['tag'][TypeDict['tag'].index(tt) - 1]
                    if cur_tag == 'networkC':  # networkC -> object -> distField
                        trans_net = {}
                        trans_net['before'] = [TypeDict['id'][TypeDict['tag'].index(tt) - 1]]
                        trans_net['after'] = [str(self.core_id)]
                        transwithin.append(trans_net)
                        # add object in types
                        dist_index = [i for i, j in enumerate(self.coreConTrans['types']) if j['type'] == 'distfield'][0]
                        self.coreConTrans.setdefault('types', []).append({'type': 'object', 'id': str(self.core_id), 'keyword': self.coreConTrans['types'][dist_index - 1]['keyword']})
                        # object -> distField
                        trans = {}
                        trans['before'] = [str(self.core_id)]
                        trans['after'] = [TypeDict['id'][TypeDict['tag'].index(tt)]]
                        transwithin.append(trans)
                        self.core_id += 1
                    elif cur_tag == 'coreC':
                        trans = {}
                        trans['before'] = [TypeDict['id'][TypeDict['tag'].index(tt) - 1]]
                        trans['after'] = [TypeDict['id'][TypeDict['tag'].index(tt)]]
                        transwithin.append(trans)
            elif tt == 'location' and 'allocation' not in TypeDict['tag']:
                trans = {}
                trans['before'] = [TypeDict['id'][TypeDict['tag'].index(tt) - 1]]
                trans['after'] = [TypeDict['id'][TypeDict['tag'].index(tt)]]
                transwithin.append(trans)
            elif tt == 'serviceobj':
                s_in = TypeDict['tag'].index(tt)
                trans = {}
                if s_in - 2 >= 0 and TypeDict['tag'][s_in - 2] == 'destination':
                    if s_in - 3 >= 0 and TypeDict['tag'][
                        s_in - 3] == 'origin':  # ['origin', 'destination', 'networkC', 'serviceObj'], remove 'roadData'
                        if len(TypeDict['id'][
                                   s_in - 3]) == 2:  # [['grid', 'centroid'], 'destination', 'networkC', 'serviceObj'], remove 'roadData'
                            trans['before'] = [TypeDict['id'][s_in - 3][0]]
                            trans['after'] = [TypeDict['id'][s_in - 3][1]]
                            transwithin.append(trans)
                        # origin: TypeDict['id'][s_in - 3], destination: TypeDict['id'][s_in - 2], remove roadData
                        # networkC is not used here.
                        trans = {}
                        trans['before'] = [TypeDict['id'][s_in - 3][-1], TypeDict['id'][s_in - 2][-1]]
                        trans['after'] = [TypeDict['id'][s_in]]
                        transwithin.append(trans)
                    elif s_in - 3 < 0 or TypeDict['tag'][0] == 'destination':  # ['destination', 'networkC', 'serviceObj'], remove 'roadData'
                        trans['before'] = [TypeDict['id'][s_in - 2][-1]]
                        trans['after'] = [TypeDict['id'][s_in]]
                        transwithin.append(trans)
                elif s_in - 2 >= 0 and TypeDict['tag'][
                    s_in - 2] == 'origin':  # ['origin', 'networkC', 'serviceObj'], remove 'roadData'
                    if len(TypeDict['id'][s_in - 2]) == 2:  # [['grid', 'centroid'], 'networkC', 'serviceObj'], remove 'roadData'
                        trans['before'] = [TypeDict['id'][s_in - 2][0]]
                        trans['after'] = [TypeDict['id'][s_in - 2][1]]
                        transwithin.append(trans)
                    trans = {}
                    trans['before'] = [TypeDict['id'][s_in - 2][-1]]
                    trans['after'] = [TypeDict['id'][s_in]]
                    transwithin.append(trans)
            elif (tt == 'networkC' or tt == 'networkQ') and (
                    'destination' in TypeDict['tag'] or 'origin' in TypeDict['tag']) and 'serviceobj' not in TypeDict[
                'tag']:
                n_in = TypeDict['tag'].index(tt)
                trans = {}
                if n_in - 1 >= 0 and TypeDict['tag'][n_in - 1] == 'destination':
                    if n_in - 2 >= 0 and TypeDict['tag'][n_in - 2] == 'origin':  # ['origin', 'destination', 'networkC'] //'roadData',
                        if len(TypeDict['id'][n_in - 2]) == 2:  # [['grid', 'centroid'], 'destination', 'networkC'] //'roadData'
                            trans['before'] = [TypeDict['id'][n_in - 2][0]]
                            trans['after'] = [TypeDict['id'][n_in - 2][1]]
                            transwithin.append(trans)
                        # origin: TypeDict['id'][n_in - 2], destination: TypeDict['id'][n_in - 1], // remove roadData:TypeDict['id'][n_in - 1]
                        trans = {}
                        trans['before'] = [TypeDict['id'][n_in - 2][-1], TypeDict['id'][n_in - 1][-1]]
                        trans['after'] = [TypeDict['id'][n_in]]
                        transwithin.append(trans)
                    elif n_in - 1 == 0 :  # ['destination', 'networkC'] //'roadData'
                        trans['before'] = [TypeDict['id'][n_in - 1][-1]]
                        trans['after'] = [TypeDict['id'][n_in]]
                        transwithin.append(trans)
                elif n_in - 1 >= 0 and TypeDict['tag'][n_in - 1] == 'origin':  # ['origin', 'networkC'] //'roadData',
                    if len(TypeDict['id'][n_in - 1]) == 2:  # [['grid', 'centroid'], 'networkC'] //'roadData',
                        trans['before'] = [TypeDict['id'][n_in - 1][0]]
                        trans['after'] = [TypeDict['id'][n_in - 1][1]]
                        transwithin.append(trans)
                    trans = {}
                    trans['before'] = [TypeDict['id'][n_in - 1][-1]]
                    trans['after'] = [TypeDict['id'][n_in]]
                    transwithin.append(trans)
            elif tt == 'extreDist' and TypeDict['tag'][TypeDict['tag'].index('extreDist')-1] == 'networkQ':
                trans = {}
                trans['before'] = [TypeDict['id'][TypeDict['tag'].index('extreDist') - 1]]
                trans['after'] = [str(self.core_id)]
                transwithin.append(trans)
                # add object quality in types
                net_index = [i for i, j in enumerate(self.coreConTrans['types']) if j['id'] == trans['before'][0]][0]
                self.coreConTrans.setdefault('types', []).append(
                    {'type': 'objectquality', 'id': str(self.core_id), 'keyword': TypeDict['text'][TypeDict['tag'].index('extreDist')] + ' ' + self.coreConTrans['types'][net_index]['keyword'], 'measureLevel': 'ratio'})
                self.core_id += 1
            elif tt == 'compareR' and len(TypeDict['tag']) == 2:
                trans = {}
                trans['before'] = [TypeDict['id'][TypeDict['tag'].index(tt)]]
                trans['after'] = [str(self.core_id)]
                transwithin.append(trans)
                self.coreConTrans.setdefault('types', []).append(self.new_type(trans['before'][0]))
                self.core_id += 1
            elif tt == 'coreC' and 'serviceobj' not in TypeDict['tag'] and 'networkC' not in TypeDict['tag']:
                trans = {}
                if 'destination' in TypeDict['tag']:
                    if 'origin' in TypeDict['tag']:  # access score
                        oin = TypeDict['tag'].index('origin')
                        if len(TypeDict['id'][oin]) == 2:
                            trans['before'] = [TypeDict['id'][oin][0]]
                            trans['after'] = [TypeDict['id'][oin][1]]
                            transwithin.append(trans)
                        trans = {}
                        trans['before'] = [TypeDict['id'][oin][-1],
                                           TypeDict['id'][TypeDict['tag'].index('destination')][-1]]
                        trans['after'] = [TypeDict['id'][TypeDict['tag'].index('coreC')]]
                        transwithin.append(trans)
                    elif 'origin' not in TypeDict['tag']:  # Euclidean distance to object
                        trans = {}
                        trans['before'] = [TypeDict['id'][TypeDict['tag'].index('destination')][-1]]
                        trans['after'] = [TypeDict['id'][TypeDict['tag'].index('coreC')]]
                        transwithin.append(trans)
                else:
                    if coreC_sign == 1:
                        continue
                    else:
                        coreC_loc = [x for x, y in enumerate(TypeDict['tag']) if y == 'coreC']
                        for coreC_l in coreC_loc:
                            if coreC_l < coreC_loc[-1]:
                                trans = {}
                                trans['before'] = [TypeDict['id'][coreC_l]]
                                trans['after'] = [TypeDict['id'][coreC_l + 1]]
                                transwithin.append(trans)
                    coreC_sign = 1

        if 'networkC' in TypeDict['tag'] and TypeDict['tag'].index('networkC') + 1 < len(TypeDict['tag']) and TypeDict['tag'][TypeDict['tag'].index('networkC') + 1] == 'coreC':
            net_index = TypeDict['tag'].index('networkC')
            trans = {}
            trans['before'] = [TypeDict['id'][net_index]]
            trans['after'] = [TypeDict['id'][net_index+1]]
            transwithin.append(trans)

        return transwithin


    # generate type for a subset of a concept. only change id. keywords and type remain same.
    def new_type(self, curid):
        newtype_index = [i for i, j in enumerate(self.coreConTrans['types']) if j['id'] == curid][0]  # find index for the subset transcross_condi['after']
        newtype = self.coreConTrans['types'][newtype_index].copy()  # copy type for the subset
        newtype['id'] = str(self.core_id)  # update id for the subset

        return newtype


    # Input coreTypeDict = coreTypes:
    #   {'funcRole': ['condition', 'condition', 'measure', 'extent', 'temEx'],
    # 	 'types': [{'tag': ['coreC', 'distField', 'boolField'], 'text': ['object 1', 'from', ''], 'id': ['0', '1', '2']},
    # 			   {'tag': ['coreC'], 'text': ['objectquality 0 boolean'], 'id': ['3']},
    # 			   {'tag': ['coreC'], 'text': ['object 0'], 'id': ['4']},
    # 			   ['Utrecht'],
    # 			   ['2030']]}
    def write_trans(self, coreTypeDict):
        try:
            coretrans = []
            subis = []
            conis = []
            supis = []
            meais = []
            mea1is = []
            con_supis = []
            mc = []  # if condition number = 2, need to combine m*condition1 and m*condition2

            if 'subcon' in coreTypeDict['funcRole']:
                subis = [x for x, y in enumerate(coreTypeDict['funcRole']) if y == 'subcon']
            if 'condition' in coreTypeDict['funcRole']:
                conis = [x for x, y in enumerate(coreTypeDict['funcRole']) if
                         (y == 'condition' and coreTypeDict['types'][x]['tag'])]
            if 'support' in coreTypeDict['funcRole']:
                supis = [x for x, y in enumerate(coreTypeDict['funcRole']) if y == 'support']
            if 'measure' in coreTypeDict['funcRole']:
                meais = [x for x, y in enumerate(coreTypeDict['funcRole']) if y == 'measure']
            if 'measure1' in coreTypeDict['funcRole']:
                mea1is = [x for x, y in enumerate(coreTypeDict['funcRole']) if y == 'measure1']

            if supis:
                conar = numpy.array(conis)
                supar = numpy.array(supis)
                con_supis = list(conar[conar < supar])
                con_meais = [x for x in conis if x not in con_supis]
            else:
                con_meais = conis

            if subis:
                if len(coreTypeDict['types'][subis[0]]['tag']) > 1:
                    if 'compareR' in coreTypeDict['types'][subis[0]]['tag'] and coreTypeDict['types'][subis[0]][
                        'tag'].index('compareR') + 1 < 2 and 'pro' not in coreTypeDict['types'][subis[0]]['text'][
                        coreTypeDict['types'][subis[0]]['tag'].index('compareR') + 1]:
                        sub_trans = self.write_trans_within(coreTypeDict['types'][subis[0]])
                        coretrans.extend(sub_trans)
                if coreTypeDict['funcRole'][subis[0] + 1] == 'condition':
                    transcross = {}
                    transcross['before'] = [coreTypeDict['types'][subis[0] + 1]['id'][0],
                                            coreTypeDict['types'][subis[0]]['id'][-1]]
                    transcross['after'] = [str(self.core_id)]
                    self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][subis[0] + 1]['id'][0]))
                    coreTypeDict['types'][subis[0] + 1]['id'][0] = transcross['after'][0]
                    self.core_id += 1
                    coretrans.append(transcross)

            if con_supis:
                if len(coreTypeDict['types'][con_supis[0]]['tag']) > 1:
                    con_sup_trans = self.write_trans_within(coreTypeDict['types'][con_supis[0]])
                    coretrans.extend(con_sup_trans[0])
                transcross = {}
                transcross['before'] = [coreTypeDict['types'][supis[0]]['id'][0],
                                        coreTypeDict['types'][con_supis[0]]['id'][-1]]
                transcross['after'] = [str(self.core_id)]
                coretrans.append(transcross)
                self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][supis[0]]['id'][0]))
                coreTypeDict['types'][supis[0]]['id'][0] = transcross['after'][0]
                self.core_id += 1

            if supis and len(coreTypeDict['types'][supis[0]]['tag']) > 1:
                sup_trans = self.write_trans_within(coreTypeDict['types'][supis[0]])
                coretrans.extend(sup_trans)

            if con_meais:
                for ci in con_meais:
                    if any('proportion' in e for e in coreTypeDict['types'][ci]['text']):
                        amount_id = coreTypeDict['types'][ci]['id'][0:-1]
                        if amount_id:
                            transcross = {}
                            transcross['before'] = amount_id
                            transcross['after'] = [coreTypeDict['types'][ci]['id'][-1]]
                            # Which park has the highest proportion of bald eagles to the bird totals in Texas, extremaR is not considered here.
                            if coreTypeDict['types'][meais[0]]['tag'] == ['coreC']:
                                transcross['key'] = coreTypeDict['types'][meais[0]]['id'][0]
                            coretrans.append(transcross)
                        elif not amount_id and len(coreTypeDict['types'][ci]['tag']) > 1:
                            con_mea_trans = self.write_trans_within(coreTypeDict['types'][ci])
                            coretrans.extend(con_mea_trans)
                            if 'compareR' in coreTypeDict['types'][ci]['tag']:
                                compR_index = coreTypeDict['types'][ci]['tag'].index('compareR')
                                coreTypeDict['types'][ci]['id'][compR_index] = con_mea_trans[0]['after'][0]
                    elif len(coreTypeDict['types'][ci]['tag']) > 1 and not any(
                            'aggre' in e for e in coreTypeDict['types'][ci]['tag']) and not any(
                            'proportion' in e for e in coreTypeDict['types'][ci]['text']):
                        con_mea_trans = self.write_trans_within(coreTypeDict['types'][ci])
                        coretrans.extend(con_mea_trans)
                        if 'compareR' in coreTypeDict['types'][ci]['tag']:
                            compR_index = coreTypeDict['types'][ci]['tag'].index('compareR')
                            coreTypeDict['types'][ci]['id'][compR_index] = con_mea_trans[0]['after'][0]

            if meais:
                if any('proportion' in e for e in coreTypeDict['types'][meais[0]]['text']):
                    amount_id = coreTypeDict['types'][meais[0]]['id'][0:-1]
                    if amount_id:
                        if supis and not con_meais:
                            for a in amount_id:
                                a_index = coreTypeDict['types'][meais[0]]['id'].index(a)
                                if 'amount' in coreTypeDict['types'][meais[0]]['text'][a_index]:
                                    transcross = {}  # objconA * support -> content Amount
                                    transcross['before'] = [a, coreTypeDict['types'][supis[0]]['id'][-1]]
                                    transcross['after'] = [str(self.core_id)]
                                    transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                                    coretrans.append(transcross)
                                    self.coreConTrans.setdefault('types', []).append(self.new_type(a))
                                    coreTypeDict['types'][meais[0]]['id'][a_index] = transcross['after'][0]
                                    self.core_id += 1
                                elif 'object' in coreTypeDict['types'][meais[0]]['text'][a_index] or 'event' in coreTypeDict['types'][meais[0]]['text'][a_index]:
                                    transcross = {}  # object * support -> object amount
                                    transcross['before'] = [a, coreTypeDict['types'][supis[0]]['id'][-1]]
                                    transcross['after'] = [str(self.core_id)]
                                    transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                                    coretrans.append(transcross)
                                    self.coreConTrans.setdefault('types', []).append(
                                        {'type': 'amount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                                    coreTypeDict['types'][meais[0]]['id'][coreTypeDict['types'][meais[0]]['id'].index(a)] = transcross['after'][0]  #why change id?
                                    self.core_id += 1
                                elif 'field' in coreTypeDict['types'][meais[0]]['text'][a_index]: # percentage of water areas for each PC4
                                    transcross = {}  #  field * support -> field coverage amount
                                    transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0], coreTypeDict['types'][supis[0]]['id'][-1]]
                                    transcross['after'] = [str(self.core_id)]
                                    transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                                    coretrans.append(transcross)
                                    self.coreConTrans.setdefault('types', []).append(
                                        {'type': 'covamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                                    self.core_id += 1
                            if not mea1is:
                                if len(coreTypeDict['types'][meais[0]]['id']) > 2:  # [amount+amount, proportion]
                                    transcross = {}  # objconA * objconA  = proportion
                                    transcross['before'] = coreTypeDict['types'][meais[0]]['id'][0:-1]
                                    transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                    transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                                    coretrans.append(transcross)
                                elif len(coreTypeDict['types'][meais[0]]['id']) == 2:  # [field/object/event, proportion]
                                    transcross = {}  # support -> support coverage amount
                                    transcross['before'] = [coreTypeDict['types'][supis[0]]['id'][-1]]
                                    transcross['after'] = [str(self.core_id)]
                                    coretrans.append(transcross)
                                    self.coreConTrans.setdefault('types', []).append(
                                        {'type': 'covamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                                    # field coverage amount * support coverage amount = proportion
                                    transcross = {}
                                    transcross['before'] = [str(self.core_id-1), str(self.core_id)]
                                    transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                    transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                                    coretrans.append(transcross)
                                    self.core_id += 1
                            elif mea1is:
                                a1 = coreTypeDict['types'][mea1is[0]]['id'][-1]
                                transcross = {}
                                transcross['before'] = [a1, coreTypeDict['types'][supis[0]]['id'][-1]]
                                transcross['after'] = [str(self.core_id)]
                                transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(self.new_type(a1))
                                coreTypeDict['types'][mea1is[0]]['id'][coreTypeDict['types'][mea1is[0]]['id'].index(a1)] = \
                                    transcross['after'][0]
                                self.core_id += 1
                                transcross = {}  # objconA * objconA  = proportion
                                transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                        coreTypeDict['types'][mea1is[0]]['id'][-1]]
                                transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                coretrans.append(transcross)
                        elif con_meais and not supis:
                            if 'id' not in coreTypeDict['types'][con_meais[0]]:  # compareR or extremaR
                                transcross = {}
                                transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                                transcross['after'] = [str(self.core_id)]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                                self.core_id += 1
                            else:
                                transcross = {}  # objconA * condi = objconA_u  or field * condi = field_u
                                transcross['before'] = [coreTypeDict['types'][con_meais[0]]['id'][-1],
                                                        coreTypeDict['types'][meais[0]]['id'][0]]
                                transcross['after'] = [str(self.core_id)]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(
                                    self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                                self.core_id += 1
                            if mea1is:
                                transcross = {}
                                transcross['before'] = [str(self.core_id-1),
                                                        coreTypeDict['types'][mea1is[0]]['id'][0]]
                                transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                transcross['key'] = self.coreConTrans['extent'][0]
                                coretrans.append(transcross)
                                self.core_id += 1
                            else:
                                if any('conamount' in e for e in coreTypeDict['types'][meais[0]]['text']):
                                    transcross = {}  # objconA_u * objconA = proportion for [condition, objconA, proportion]
                                    transcross['before'] = [str(self.core_id-1),
                                                            coreTypeDict['types'][meais[0]]['id'][0]]
                                    transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                    transcross['key'] = self.coreConTrans['extent'][0]
                                    coretrans.append(transcross)
                                    self.core_id += 1
                                elif any('field' in e for e in coreTypeDict['types'][meais[0]]['text']):
                                    transcross = {}  # field_u -> field coverage amount
                                    transcross['before'] = [str(self.core_id-1)]  # field_u
                                    transcross['after'] = [str(self.core_id)]  # covamount
                                    coretrans.append(transcross)
                                    self.coreConTrans.setdefault('types', []).append(
                                        {'type': 'covamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                                    self.core_id += 1
                                    if 'id' not in coreTypeDict['types'][con_meais[0]]:  # noise larger than 70 db
                                        #  extent -> extent coverage amount
                                        transcross = {}
                                        transcross['before'] = self.coreConTrans['extent']
                                        transcross['after'] = [str(self.core_id)]
                                        coretrans.append(transcross)
                                        self.coreConTrans.setdefault('types', []).append(
                                            {'type': 'covamount', 'id': str(self.core_id), 'keyword': '',
                                             'measureLevel': 'era'})
                                        # field coverage amount, extent coverage amount -> proportion
                                        transcross = {}
                                        transcross['before'] = [str(self.core_id - 1), str(self.core_id)]  # core_id-1 = field covamount, core_id = extent covamount
                                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                        transcross['key'] = self.coreConTrans['extent'][0]
                                        coretrans.append(transcross)
                                        self.core_id += 1
                                    else:
                                        # condition -> conidtion coverage amount
                                        transcross = {}
                                        transcross['before'] = [coreTypeDict['types'][con_meais[0]]['id'][-1]]  # boolfiled or distfield
                                        transcross['after'] = [str(self.core_id)]
                                        coretrans.append(transcross)
                                        self.coreConTrans.setdefault('types', []).append(
                                            {'type': 'covamount', 'id': str(self.core_id), 'keyword': '',
                                             'measureLevel': 'era'})
                                        # field coverage amount * condition coverage amount = proportion
                                        transcross = {}
                                        transcross['before'] = [str(self.core_id - 1), str(self.core_id)]
                                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                        transcross['key'] = str(self.core_id)
                                        coretrans.append(transcross)
                                        self.core_id += 1
                                else:
                                    transcross = {}  # object_u -> object_u amount
                                    transcross['before'] = [str(self.core_id-1)]
                                    transcross['after'] = [str(self.core_id)]
                                    transcross['key'] = self.coreConTrans['extent'][0]  # object to amount need a key, to covamount donot a key?
                                    coretrans.append(transcross)
                                    self.coreConTrans.setdefault('types', []).append(
                                        {'type': 'amount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                                    self.core_id += 1
                                    # object -> object amount
                                    transcross = {}  # object -> object amount
                                    transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                                    transcross['after'] = [str(self.core_id)]
                                    transcross['key'] = self.coreConTrans['extent'][0]
                                    coretrans.append(transcross)
                                    self.coreConTrans.setdefault('types', []).append(
                                        {'type': 'amount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                                    # object amount * condition coverage amount = proportion
                                    transcross = {}
                                    transcross['before'] = [str(self.core_id - 1), str(self.core_id)]
                                    transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                    transcross['key'] = self.coreConTrans['extent'][0]
                                    coretrans.append(transcross)
                                    self.core_id += 1
                        elif not supis and not con_meais:
                            # extent -> extent covamount
                            trans_ext = {}
                            trans_ext['before'] = [self.coreConTrans['extent'][0]]
                            trans_ext['after'] = [str(self.core_id)]
                            coretrans.append(trans_ext)
                            self.coreConTrans.setdefault('types', []).append(
                                {'type': 'covamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                            self.core_id += 1
                            if any('field' in e for e in coreTypeDict['types'][meais[0]]['text']): # What is the percentage of noise polluted areas in placename0
                                # field -> field covamount
                                transcross = {}
                                transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                                transcross['after'] = [str(self.core_id)]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(
                                    {'type': 'covamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                            else:
                                obj_loc = [coreTypeDict['types'][meais[0]]['text'].index(i) for i in coreTypeDict['types'][meais[0]]['text'] if 'object' in i]
                                if obj_loc:
                                    # obj -> amount
                                    trans_obj = {}
                                    trans_obj['before'] = [coreTypeDict['types'][meais[0]]['id'][obj_loc[0]]]
                                    trans_obj['after'] = [str(self.core_id)]
                                    trans_obj['key'] = self.coreConTrans['extent'][0]
                                    coretrans.append(trans_obj)
                                    self.coreConTrans.setdefault('types', []).append(
                                        {'type': 'amount', 'id': str(self.core_id), 'keyword': '',
                                         'measureLevel': 'era'})
                                    coreTypeDict['types'][meais[0]]['id'][obj_loc[0]] = trans_obj['after'][0]
                            # proportion
                            if len(amount_id) == 2:
                                transcross = {}
                                transcross['before'] = coreTypeDict['types'][meais[0]]['id'][0:-1]
                                transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                transcross['key'] = self.coreConTrans['extent'][0]
                                coretrans.append(transcross)
                            elif len(amount_id) == 1:
                                transcross = {}
                                transcross['before'] = [str(self.core_id), trans_ext['after'][0]]
                                transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                transcross['key'] = self.coreConTrans['extent'][0]
                                coretrans.append(transcross)
                                self.core_id += 1
                        elif supis and con_meais:
                            # object* condi = object_u or field * condi = field_u  or objconA * condi = objconA_u
                            if 'compareR' in coreTypeDict['types'][con_meais[0]]['tag'] and len(coreTypeDict['types'][con_meais[0]]['tag']) == 1:
                                compR_trans = {}
                                compR_trans['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                                compR_trans['after'] = [str(self.core_id)]
                                coretrans.append(compR_trans)
                            else:
                                transcross_condi = {}
                                transcross_condi['before'] = [coreTypeDict['types'][con_meais[0]]['id'][-1],
                                                        coreTypeDict['types'][meais[0]]['id'][0]]
                                transcross_condi['after'] = [str(self.core_id)]
                                coretrans.append(transcross_condi)
                            newtype = self.new_type(coreTypeDict['types'][meais[0]]['id'][0])
                            self.coreConTrans.setdefault('types', []).append(newtype)
                            self.core_id += 1
                            # object_u * support -> object_u amount or field_u * support -> field_u covamount, key required
                            transcross = {}
                            transcross['before'] = [newtype['id'], coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [str(self.core_id)]
                            transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                            if newtype['type'] == 'object':
                                self.coreConTrans.setdefault('types', []).append({'type': 'amount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                            elif newtype['type'] == 'field':
                                self.coreConTrans.setdefault('types', []).append({'type': 'covamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                            self.core_id += 1
                            # object * support = object_u_u amount  key required
                            if newtype['type'] == 'object':
                                transcross_sup = {}
                                transcross_sup['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                            coreTypeDict['types'][supis[0]]['id'][-1]]
                                transcross_sup['after'] = [str(self.core_id)]
                                transcross_sup['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                                self.coreConTrans.setdefault('types', []).append({'type': 'amount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                            elif newtype['type'] == 'field': # support -> covamount if field,
                                transcross_sup = {}
                                transcross_sup['before'] = [coreTypeDict['types'][supis[0]]['id'][-1]]
                                transcross_sup['after'] = [str(self.core_id)]
                                self.coreConTrans.setdefault('types', []).append({'type': 'covamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                            coretrans.append(transcross_sup)
                            # object_u amount * object_u_u amount -> proportion or field_u covamount * field_u_u covamount -> proportion
                            transcross_pro = {}
                            transcross_pro['before'] = [str(self.core_id-1), str(self.core_id)]
                            transcross_pro['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            transcross_pro['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross_pro)
                            self.core_id += 1
                    else:
                        if con_meais and not supis:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][con_meais[0]]['id'][-1], coreTypeDict['types'][meais[0]]['id'][0]]
                            transcross['after'] = [str(self.core_id)]
                            if 'distfield' in coreTypeDict['types'][0]['tag']:
                                dist_index = [i for i, j in enumerate(self.coreConTrans['types']) if j['type'] == 'distfield'][0]
                                if coreTypeDict['types'][0]['tag'][dist_index-1] == 'networkC':
                                    transcross['key'] = str(self.core_id-1)
                                elif coreTypeDict['types'][0]['tag'][dist_index-1] == 'coreC':
                                    transcross['key'] = coreTypeDict['types'][0]['id'][dist_index-1]
                            coretrans.append(transcross)
                            # add new proportion type in coreConTrans[types]
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                            self.core_id += 1
                        elif supis and not con_meais:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][supis[0]]['id'][-1],
                                                    coreTypeDict['types'][meais[0]]['id'][0]]
                            transcross['after'] = [str(self.core_id)]
                            transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                            self.core_id += 1
                elif any('objconobjconpro' in e for e in coreTypeDict['types'][meais[0]]['text']) and any('object' in e for e in coreTypeDict['types'][meais[0]]['text']):
                    if supis and not con_meais:
                        # object/objconA * support - > objconA
                        trans_sup = {}
                        trans_sup['before'] = [coreTypeDict['types'][meais[0]]['id'][0], coreTypeDict['types'][supis[0]]['id'][0]]
                        trans_sup['after'] = [str(self.core_id)]
                        trans_sup['key'] = coreTypeDict['types'][supis[0]]['id'][0]
                        coretrans.append(trans_sup)
                        self.coreConTrans.setdefault('types', []).append({'type': 'objconamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                        self.core_id += 1
                        # objconA * a unknown objconA -> proportion
                        transcross = {}
                        transcross['before'] = [trans_sup['after'][0], str(self.core_id)]
                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                        transcross['key'] = coreTypeDict['types'][supis[0]]['id'][0]
                        coretrans.append(transcross)
                        self.coreConTrans.setdefault('types', []).append(
                            {'type': 'objconamount', 'id': str(self.core_id), 'keyword': '', 'measureLevel': 'era'})
                        self.core_id += 1
                elif any('conamount' in e for e in coreTypeDict['types'][meais[0]]['text']) and not any(
                        'aggre' in e for e in coreTypeDict['types'][meais[0]]['tag']) and not any(
                    'proportion' in e for e in coreTypeDict['types'][meais[0]]['text']) and not any(
                    'covamount' in e for e in coreTypeDict['types'][meais[0]]['text']):
                    if supis and not con_meais:
                        if len(coreTypeDict['types'][meais[0]]['tag']) == 2:  # conamount of coreC
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                        else:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [str(self.core_id)]
                            transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                    elif con_meais and not supis:
                        if len(coreTypeDict['types'][meais[0]]['tag']) > 1:
                            # object * condition -> object_u
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][con_meais[0]]['id'][-1]]
                            transcross['after'] = [str(self.core_id)]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                            transcross = {}
                            transcross['before'] = [str(self.core_id)]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            transcross['key'] = self.coreConTrans['extent'][0]
                            coretrans.append(transcross)
                            self.core_id += 1
                        else:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][con_meais[0]]['id'][-1]]
                            transcross['after'] = [str(self.core_id)]
                            transcross['key'] = self.coreConTrans['extent'][0]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                            self.core_id += 1
                    elif con_meais and supis:
                        for ci in con_meais:
                            if len(coreTypeDict['types'][ci]['tag']) == 1 and (
                                    coreTypeDict['types'][ci]['tag'][0] == 'extremaR' or coreTypeDict['types'][ci]['tag'][
                                0] == 'compareR'):
                                transcross = {}
                                transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                                transcross['after'] = [str(self.core_id)]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(
                                    self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                                coreTypeDict['types'][meais[0]]['id'][0] = transcross['after'][0]
                                self.core_id += 1
                            else:
                                transcross = {}
                                transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                        coreTypeDict['types'][ci]['id'][-1]]
                                transcross['after'] = [str(self.core_id)]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(
                                    self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                                coreTypeDict['types'][meais[0]]['id'][0] = transcross['after'][0]
                                self.core_id += 1
                        if len(coreTypeDict['types'][meais[0]]['tag']) == 2:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                    elif not con_meais and not supis:
                        transcross = {}
                        transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                        transcross['key'] = self.coreConTrans['extent'][0]
                        coretrans.append(transcross)
                elif any('covamount' in e for e in coreTypeDict['types'][meais[0]]['text']) and not any(
                        'aggre' in e for e in coreTypeDict['types'][meais[0]]['tag']):
                    if not supis and not con_meais:
                        if 'loc' in coreTypeDict['types'][meais[0]]['text'][-1] and 'weight' in coreTypeDict:
                            if coreTypeDict['weight'] == 2:
                                # transformation within weight
                                trans_weight = {}
                                trans_weight['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                                trans_weight['after'] = [coreTypeDict['types'][meais[0]]['id'][1]]
                                if 'conamount' in coreTypeDict['types'][meais[0]]['text'][1]:
                                    trans_weight['key'] = coreTypeDict['types'][meais[0]]['id'][2]
                                coretrans.append(trans_weight)
                                # weight output * measure input -> covamount loc
                                transcross = {}
                                transcross['before'] = coreTypeDict['types'][meais[0]]['id'][1:3]
                                transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                coretrans.append(transcross)
                            elif coreTypeDict['weight'] == 1:
                                # weight * measure input -> covamount loc
                                transcross = {}
                                transcross['before'] = coreTypeDict['types'][meais[0]]['id'][0:2]
                                transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                coretrans.append(transcross)
                        else:
                            cov_trans = self.write_trans_within(coreTypeDict['types'][meais[0]])
                            coretrans.extend(cov_trans)
                    elif supis and not con_meais:
                        if 'location' in coreTypeDict['types'][meais[0]]['tag']:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-2]]
                            coretrans.append(transcross)
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][-2]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            coretrans.append(transcross)
                        else:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            if 'era' in coreTypeDict['types'][meais[0]]['text'][-1].split(' '):
                                transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                    elif con_meais and not supis:
                        if 'location' in coreTypeDict['types'][meais[0]]['tag']:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][conis[0]]['id'][-1]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-2]]
                            coretrans.append(transcross)
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][-2]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            coretrans.append(transcross)
                        else:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][conis[0]]['id'][-1]]
                            transcross['after'] = [str(self.core_id)]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                            transcross = {}
                            transcross['before'] = [str(self.core_id)]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            coretrans.append(transcross)
                            self.core_id += 1
                    elif supis and con_meais:
                        transcross = {}
                        transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                coreTypeDict['types'][supis[0]]['id'][-1]]
                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][1]]
                        coretrans.append(transcross)
                        if 'location' in coreTypeDict['types'][meais[0]]['tag']:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][1]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            coretrans.append(transcross)
                elif any('aggre' in e for e in coreTypeDict['types'][meais[0]]['tag']):
                    if len(coreTypeDict['types'][meais[0]]['tag']) - 1 > 1:
                        befagg_trans = self.write_trans_within(coreTypeDict['types'][meais[0]])
                        coretrans.extend(befagg_trans)
                        if 'extreDist' in coreTypeDict['types'][0]['tag']:
                            extre_index = coreTypeDict['types'][0]['tag'].index('extreDist')
                            coreTypeDict['types'][0]['id'].insert(extre_index, str(self.core_id-1))
                    if supis:
                        transcross = {}
                        transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][-2],
                                                coreTypeDict['types'][supis[0]]['id'][-1]]
                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                        transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                        coretrans.append(transcross)
                    elif con_meais:
                        transcross = {}
                        transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][-2],
                                                coreTypeDict['types'][con_meais[0]]['id'][-1]]
                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                        coretrans.append(transcross)
                    else:
                        transcross = {}
                        transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][-2]]
                        transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                        transcross['key'] = coreTypeDict['types'][coreTypeDict['funcRole'].index('extent')][0]
                        coretrans.append(transcross)
                else:
                    if supis and not con_meais:
                        if len(coreTypeDict['types'][meais[0]]['id']) == 1:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [str(self.core_id)]
                            if 'quality' in coreTypeDict['types'][meais[0]]['text'][0]:
                                transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                            self.core_id += 1
                        else:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                    coreTypeDict['types'][supis[0]]['id'][-1]]
                            transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                            if 'quality' in coreTypeDict['types'][meais[0]]['text'][-1]:
                                transcross['key'] = coreTypeDict['types'][supis[0]]['id'][-1]
                            coretrans.append(transcross)
                    elif con_meais and not supis:
                        for ci in con_meais:
                            if len(coreTypeDict['types'][ci]['tag']) == 1 and (
                                    coreTypeDict['types'][ci]['tag'][0] == 'extremaR' or coreTypeDict['types'][ci]['tag'][
                                0] == 'compareR'):
                                transcross = {}
                                transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                                transcross['after'] = [str(self.core_id)]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                                self.core_id += 1
                            elif coreTypeDict['types'][meais[0]]['tag'][0] == 'location' or \
                                    coreTypeDict['types'][meais[0]]['tag'][0] == 'allocation':
                                transcross = {}
                                transcross['before'] = [coreTypeDict['types'][ci]['id'][-1]]
                                transcross['after'] = [coreTypeDict['types'][meais[0]]['id'][-1]]
                                coretrans.append(transcross)
                            else:
                                transcross = {}
                                transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0],
                                                        coreTypeDict['types'][ci]['id'][-1]]
                                transcross['after'] = [str(self.core_id)]
                                coretrans.append(transcross)
                                self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))
                                self.core_id += 1
                            if len(coreTypeDict['types'][meais[0]]['tag']) > 1:
                                coreTypeDict['types'][meais[0]]['id'][0] = transcross['after'][0]
                                mea_trans = self.write_trans_within(coreTypeDict['types'][meais[0]])
                                if coreTypeDict['types'][meais[0]]['tag'][-1] == "conAm":
                                    mea_trans[0]['key'] = self.coreConTrans['extent'][0]
                                coretrans.extend(mea_trans)
                                mc.append(mea_trans[-1]['after'][0])
                            else:
                                mc.append(transcross['after'][0])
                        if len(mc) > 1:
                            transcross = {}
                            transcross['before'] = mc
                            transcross['after'] = [str(self.core_id)]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(mc[0]))
                            self.core_id += 1
                    else:
                        if len(coreTypeDict['types'][meais[0]]['tag']) > 1:
                            mea_trans = self.write_trans_within(coreTypeDict['types'][meais[0]])
                            coretrans.extend(mea_trans)
                        else:
                            transcross = {}
                            transcross['before'] = [coreTypeDict['types'][meais[0]]['id'][0]]
                            transcross['after'] = [str(self.core_id)]
                            coretrans.append(transcross)
                            self.coreConTrans.setdefault('types', []).append(self.new_type(coreTypeDict['types'][meais[0]]['id'][0]))

            self.coreConTrans.setdefault('transformations', []).extend(coretrans)

        except Exception as e:
            print("============================ Exception in write_trans:")
            print(e)
            self.coreConTrans['transformations'] = []

        # [SC][TODO] why is there a return?
        return self.coreConTrans


    # [SC] the main method to be called to parse an NLP question string
    def parseQuestion(self, question):
        self.result = {}
        self.core_id = 0
        self.coreConTrans = {}  # final cctrans output

        try:
            sym = '" ? \n \t'
            self.result['question'] = question.strip(sym)

            print('---------Question---------')
            print(question)

            # [X] Tokenization
            doc = nlp_en(self.result['question'])

            # [X] Cleaning text: remove stopwords and save the tokens in a list
            token_list = []
            for word in doc:
                if not word.is_stop and not word.is_punct or word.text == ',':
                    token_list.append(word)
            sen = ' '.join(word.text for word in token_list).strip()  # Question in string without stopwords
            sen_Clean = self.word2num(sen)  # Convert numeric words into digit numbers
            self.result['cleaned_Question'] = sen_Clean

            # 【X】Identify place names
            re_Place = self.place_ner(sen_Clean)
            self.result['placename'] = re_Place[0]  # re_Place[0]: list - PlaceName

            # [X] Identify Date, Time, Quantity, Cardinal, Percent
            re_Entities = self.entity_ner(re_Place[1])  # parsed_Place[1]: sentence
            self.result.update(re_Entities[0])  # parsed_Entities[0]: dictionary - Time, Quantity, Percent, Date

            # [X] Identify Core Concept
            re_CoreCon = self.core_concept_match(re_Entities[1].lower())  # parsed_Entities[1]: sentence
            self.result.update(re_CoreCon[0])  # re_CoreCon[0]: dictionary - Core Concepts
            self.result['ner_Question'] = re_CoreCon[1]  # re_CoreCon[1] : sentence with core concepts holders

            # [X] Generate parser tree & Extract core concept transformation
            parsedQuestion = self.geo_parser(re_CoreCon[1])
            if parsedQuestion[0]:
                self.result['parseTreeStr'] = parsedQuestion[0]
            # [SC][TODO] error logging
            # if parsedQuestion[2]:
            #     error_ques.write(parsedQuestion[3] + '\n')  # questions can not be parsed in the grammar
            if parsedQuestion[1] and self.coreConTrans:
                self.result['cctrans'] = self.write_trans(parsedQuestion[1])

        except Exception as e:
            # [SC][TODO] error logging
            print("============================ Exception in parseQuestion:")
            print(e)
            # ques_incorrect = question
            # error_ques.write(ques_incorrect + '\n')

        return self.result

#################################################################################

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


# Read Core concepts.txt into a dictionary.
def load_ccdict(filePath):
    coreCon = {}
    text = []
    tag = []
    meaLevel = []  # measurement level
    with open(filePath, encoding="utf-8") as coreConcepts:
        for line in coreConcepts:
            cur = line.strip().split('\t')
            text.append(cur[0].lower())
            tag.append(cur[1].lower())
            if len(cur) == 3:
                meaLevel.append(cur[2].lower())
            else:
                meaLevel.append('NULL')
    coreCon['text'] = text
    coreCon['tag'] = tag
    coreCon['measureLevel'] = meaLevel

    return coreCon


rootPath = ""

ptypePath = f"{rootPath}Dictionary/place_type.txt"
corePath = f"{rootPath}Dictionary/coreConceptsML.txt"
networkPath = f"{rootPath}Dictionary/network.txt"

conversionRulesPath = f'{rootPath}Rules/conversionRules.json'
hConceptHierarchyPath = f'{rootPath}Rules/hConceptHierarchy.json'
measureHierarchyPath = f'{rootPath}Rules/measureHierarchy.json'


nlp_en = CustomEnglish()  # [X] Load English stopwords
nlp = en_core_web_sm.load()  # load en_core_web_sm of English for NER, noun chunks
matcher = PhraseMatcher(nlp.vocab)  # add noun phrases when doing noun_chunks
patterns = [nlp('bus stops'), nlp('driving time'), nlp('grid cell'), nlp('grid cells'), nlp('off street paths'), nlp('mean direction'),
                nlp('degree of clustering'), nlp('degree of dispersion'), nlp('fire call'), nlp('fire calls'), nlp('slope'),
                nlp('wetlands'), nlp('house totals'), nlp('fire hydrant'), nlp('fire scene'), nlp('fire scenes'), nlp('walkability'),
                nlp('owner occupied houses'), nlp('temperature in celsius'), nlp('police beat'), nlp('police beats'), nlp('mean center'),
                nlp('tornado touchdowns'), nlp('nurse practitioner services'), nlp('priority rankings'), nlp('tram stations'), nlp('tram station'),
                nlp('plumbing'), nlp('political leaning'), nlp('predicted probability surface'), nlp('fire accidents'),
                nlp('for sale'), nlp('open at'), nlp('predicted distribution probability'), nlp('senior high schools'), nlp('floodplain'),
                nlp('income of households'), nlp('interpolated surface'), nlp('average cost per acre'), nlp('high school students'),
                nlp('wind farm proposals'), nlp('planned commercial district'), nlp('protected region'), nlp('pc4 area'),
                nlp('aspect'), nlp('monthly rainfall'), nlp('hot spots and cold spots'), nlp('ski pistes'), nlp('outpatient services'),
                nlp('per household online loan application rates'), nlp('windsurfing spot'), nlp('accident'), nlp('census tract'),
                nlp('mean annual PM 2.5 concentration'), nlp('PM 2.5 concentration'), nlp('cesium 137 concentration')]
matcher.add("PHRASES", patterns)

# [SC] load the rules for annotating with cct expressions
convRules = json.load(open(conversionRulesPath))
# [SC] load concept type hierachy
hConceptHierarchyJson = json.load(open(hConceptHierarchyPath))
hConceptHierarchy = {}
# [SC] load measurement hierachy
measureHierarchyJson = json.load(open(measureHierarchyPath))
measureHierarchy = {}

parseHierarchies()

predictorELMo = Predictor.from_path(
        "https://storage.googleapis.com/allennlp-public-models/ner-elmo.2021-02-12.tar.gz")  # Allennlp Elmo-based NER

# [X] Read place type set
pt_set = set(line.strip() for line in open(ptypePath, encoding="utf-8"))
# [X] Read core concept dictionary
coreCon_dict = load_ccdict(corePath)
networkSet = set(l.strip() for l in open(networkPath, encoding="utf-8"))

pos = []
units = {'db', 'dB', 'DB', 'decibel', 'meters'}
humanWords = {'people', 'population', 'children'}
amsign = {'have', 'has', 'had', 'no'}
compR = ['lower than', 'larger than', 'at least', 'less than', 'more than', 'greater than',
             'greater than or equal to', 'smaller than', 'equal to']
cn = {'least cost route', 'least cost path', 'least costly route', 'least costly path', 'driving time', 'high school students', 'senior high schools',
          'travel time', 'forest areas', 'for sale', 'open at', 'shortest network based paths', 'tram station', 'tram stations', 'senior high school district',
          'hot spots and cold spots', 'shortest path', 'cesium 137 concentration', 'PM2.5 concentration', 'potentially deforested areas'}
removeWords = {'what', 'where', 'which', 'how', 'for', 'each', 'when', 'who', 'why', 'new', 'no', 'similar',
                   'nearest', 'most', 'to', 'at', 'low', 'high', 'aged'}
que_stru = {'measure', 'measure1', 'condition', 'subcon', 'support'}
measLevel = {'interval', 'nominal', 'ratio', 'count', 'loc', 'ordinal', 'era', 'ira', 'boolean'}



import zmq
import threading
import json

import traceback
import sys

import socket

import signal

# [SC][TODO]
import time


# [SC] to capture the keyboard interrput command (Ctrl + C)
signal.signal(signal.SIGINT, signal.SIG_DFL)

# [SC][TODO] these should be set from a command line
workerInstanceCount = 5
frontendPort = "5570"

defWorkerInstanceCount = 10
defIp = "127.0.0.1"
defFrontendPort = "5570"
frontendBind = ""
backendBind = "inproc://backend"


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
    # @return   string          The composed log text as string
    @staticmethod
    def cPrint(type, method, msg):
        msg = f"{type}: {msg} in method '{method}'"
        
        if Logger.printConsole: 
            print(msg)
        
        return msg


# [SC] this class implement a worker
class QparserWorker(threading.Thread):
    def __init__(self, context, wId):
        threading.Thread.__init__ (self)
        self.context = context
        self.wId = wId
    
    def run(self):
        methodName = "QparserWorker.run"
        
        global backendBind
    
        # [SC] connect worker to a inter-process socket from a shared context
        # [SC] zmq.DEALER si required instead of zmq.REP
        worker = self.context.socket(zmq.DEALER)
        worker.connect(backendBind)
        Logger.cPrint(Logger.INFO_TYPE, methodName, f"Started worker '{self.wId}' on a inter-process socket '{backendBind}'")
        
        while True:
            cId = ""
            qStr = ""
            
            try:
                # [SC] receive client id at first
                cId = worker.recv_string()
                # [SC] receive the question string
                qStr = worker.recv_string()
                Logger.cPrint(Logger.INFO_TYPE, methodName
                    , f"Worker '{self.wId}' received a request. Client: '{cId}'; Message: '{qStr}'") 
            except Exception as e:
                Logger.cPrint(Logger.ERROR_TYPE, methodName
                    , f"============================ Exception in worker '{self.wId}' while receiving a request from the broker")
                exc_info = sys.exc_info()
                Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
                # [SC][TODO] more graceful handling of errors is needed here
                continue
            
            msg = ""
            qParsed = {}
            
            try:
                # [SC][TODO] do work here
                # [SC][TODO] serialize the final output into a string and assign to the variable 'msg'
                parser = QuestionParser(None)
                qParsed = parser.parseQuestion(qStr)
                Logger.cPrint(Logger.INFO_TYPE, methodName, f"Parsed the question '{qStr}'")
                
                cctAnnotator = TypesToQueryConverter()
                cctAnnotator.algebraToQuery(qParsed, True, True)
                cctAnnotator.algebraToExpandedQuery(qParsed, False, False)
                Logger.cPrint(Logger.INFO_TYPE, methodName, f"Annotated the question '{qStr}'")

                # [SC] serialize the final parse tree
                msg = json.dumps(qParsed)
                Logger.cPrint(Logger.INFO_TYPE, methodName, f"The final parse tree result: \n{msg}")
            
                # [SC][TODO] for testing only
                #qParsed = {"qstr": qStr}

                # [SC][TODO] for testing only
                #time.sleep(int(qStr))
                #time.sleep(20)
                
                # [SC][TODO] for testing only
                #msg = json.dumps(qParsed)
            except Exception as e:
                eMsg = Logger.cPrint(Logger.ERROR_TYPE, methodName
                    , "============================ Exception while parsing/annotating the question")
                exc_info = sys.exc_info()
                eMsg = eMsg + "\n" + Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
                qParsed["error"] = eMsg
                msg = json.dumps(qParsed)
            finally:
                worker.send_string(cId, zmq.SNDMORE)
                worker.send_string(msg)
        
        worker.close()


# [SC] this class implement a broker mediating between workers and clients
class QparserBroker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__ (self)
        
    def run(self):
        methodName = "QparserBroker.run"
    
        global frontendBind
        global backendBind
        global workerInstanceCount
        
        # [SC] this zmq context is shared between worker and broker
        context = zmq.Context()
        
        # [SC] client connects to this socket
        frontend = context.socket(zmq.ROUTER)
        frontend.bind(frontendBind)
        Logger.cPrint(Logger.INFO_TYPE, methodName, f"Bound broker frontend to '{frontendBind}'")
        
        # [SC] worker connects to this inter-process socket
        backend = context.socket(zmq.DEALER)
        backend.bind(backendBind)
        Logger.cPrint(Logger.INFO_TYPE, methodName, f"Bound broker backend to an inter-process port '{backendBind}'")
        
        # [SC] creating worker instances
        workers = []
        for i in range(workerInstanceCount):
            worker = QparserWorker(context, i)
            worker.start()
            workers.append(worker)
        
        # [SC] creating a poller to forward clint and worker messages
        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(backend, zmq.POLLIN)
        Logger.cPrint(Logger.INFO_TYPE, methodName, "Started the poller in the broker")
        
        while True:
            # [SC][TODO] more error handling is needed
            # [SC][TODO] if two clients use the same id then the one who connects last is ignored; need to fix it
            try:
                sockets = dict(poller.poll())
                
                # [SC] received a request from a client, forwarding the request to a worker
                if sockets.get(frontend) == zmq.POLLIN:
                    # [SC] receive client id at first
                    cId = frontend.recv_string()
                    # [SC] receive the question string
                    qStr = frontend.recv_string()
                    
                    Logger.cPrint(Logger.INFO_TYPE, methodName
                        , f"Forwarding a request from a client to a worker. Client: '{cId}'; Message: '{qStr}'")
                    backend.send_string(cId, zmq.SNDMORE)
                    backend.send_string(qStr)
                
                # [SC] received a reply from the worker, forwarding the reply to the client
                if sockets.get(backend) == zmq.POLLIN:
                    # [SC] receive client id at first
                    cId = backend.recv_string()
                    # [SC] receive the reply message (parse tree)
                    msg = backend.recv_string()
                    
                    Logger.cPrint(Logger.INFO_TYPE, methodName
                        , f"Forwarding a reply from the worker to the client. Client: '{cId}'; Message: '{msg}'")
                    frontend.send_string(cId, zmq.SNDMORE)
                    frontend.send_string(msg)
            except Exception as e:
                Logger.cPrint(Logger.ERROR_TYPE, methodName, f"============================ Exception in the broker")
                exc_info = sys.exc_info()
                Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info))) 
                    
        frontend.close()
        backend.close()
        context.term()



def isPortBindable(ip, port):
    methodName = "isOpenPort"
    
    testSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        testSocket.bind((ip, int(port)))
        return True
    except Exception as e:
        Logger.cPrint(Logger.ERROR_TYPE, methodName, f"============================ Problem with the port {port} at {ip}")
        exc_info = sys.exc_info()
        Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
        return False
    finally:
        testSocket.close()


def main():
    methodName = "main"
    
    global frontendPort
    global defFrontendPort
    global frontendBind
    global defIp
    
    global workerInstanceCount
    global defWorkerInstanceCount
    
    # [SC] make sure the port is usable
    if not isPortBindable(defIp, frontendPort):
        Logger.cPrint(Logger.WARNING_TYPE, methodName, f"Cannot open port '{frontendPort}'")
        Logger.cPrint(Logger.WARNING_TYPE, methodName, f"Attempting the default port '{defFrontendPort}'")
        
        if isPortBindable(defIp, defFrontendPort):
            frontendPort = defFrontendPort
        else:
            Logger.cPrint(Logger.ERROR_TYPE, methodName, f"Cannot open the default port '{defFrontendPort}'")
            Logger.cPrint(Logger.ERROR_TYPE, methodName, f"Unable to start the server. No available ports")
            return
    
    # [SC] make sure a valid number for instance is provided
    try:
        workerInstanceCount = int(workerInstanceCount)
        if workerInstanceCount <= 0:
            raise Exception(f"Invalid worker instance count '{workerInstanceCount}'. Worker instance count should be 1 or higher integer number.")
    except Exception as e:
        Logger.cPrint(Logger.ERROR_TYPE, methodName, f"============================ Invalid worker instance count")
        exc_info = sys.exc_info()
        Logger.cPrint(Logger.ERROR_TYPE, methodName, ''.join(traceback.format_exception(*exc_info)))
        
        Logger.cPrint(Logger.WARNING_TYPE, methodName, f"Using the default worker instance count '{defWorkerInstanceCount}'")
        workerInstanceCount = defWorkerInstanceCount
    
    # [SC] compose bind address for a frontend client
    frontendBind = f"tcp://{defIp}:{frontendPort}"

    # [SC] start the broker server
    server = QparserBroker()
    server.start()
    server.join()


if __name__ == "__main__":
    main()