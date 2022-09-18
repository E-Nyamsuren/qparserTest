grammar GeoAnQu;

// parser rules start with lowercase letters, lexer rules with uppercase
//start
start : ((WH ((AUX (extremaR|extreDist)? measure) | (measure AUX? false?))) | (measure 'that'? AUX? false?))
        (condition ('and'|false)?)* measure1?
        (('with'|'that' AUX?)? false? subcon)?
        (('for each'|'per') support)? condition?
        (('in'|'near')? (extent 'and'?)+)*
        (('in'|'on'|'from')? temEx 'to'? temEx?)? ;
false : Flase ;
measure: location | (conAm coreC) |
         (aggre? DIGIT? (coreC 'and'?)+ (('of'|'for'|'to'|'during'|'per') DIGIT? 'each'? 'new'? (coreC|distBandNei))* weight?) |
         (aggre? (networkC|networkQ|coreC) ((('to'|'through')? destination)* (('from'|'for'|'of')? 'each'? origin)* ('to'? destination)*)) |
         (coreC 'by' networkC);
//|(aggre? coreC 'and'?)+ (('for'|'of'|'to'|'by'|'through') ('new'? 'each'? DIGIT? (extremaR|extreDist)? (coreC|grid|distBandNei| 'and'?)+))* ;
//measure: location | (coreC (('for'|'of'|'to'|'by'|'from') ('new'? coreC | grid))* (('to'|'from'|'of') extrema? coreC)?) ;
measure1: 'to' coreC;
location: (Location1 AUX? false? (allocation|(extremaR? (coreC 'and'?)+ ('of' coreC)?)))|Location2;
conAm: ConAm ;
weight: ('weighted by' aggre? coreC ('of' coreC)?) | ('with similar' aggre? coreC);
allocation: ('best site'|'best sites') ('for'|'of') 'new'? coreC ;
condition: boolField |
           (topoR (grid|(coreC ('of' ((coreC 'from' origin 'to' destination)|coreC))?)|densityNei))|
           ('with'? boolR 'from'? DIGIT? (extremaR|aggre)? coreC? (('of' coreC 'to' coreC+)|('of'? compareR? (quantity|coreC))|date|time|percent)?)|
           (('with'|'of')? compareR (quantity|distField|(DIGIT? coreC)))|
           ((extremaR|distanceR) ('each'? coreC ('of' coreC)?)?)|
           topoRIn | coreC | date ;  // //(coreC time? 'of'? coreC?) // (('with'|'that' AUX?)? false? subcon)?
grid: quantity? ('grids'|'grid cells'|'grid'|'grid cell'|'hexagonal grids'|'hexagonal grid'|'hexagon grid') ('with' 'diameter of'? quantity)? ;
boolField: (topoR|compareR|extremaR)? (distField|serviceObj);
distField: ((quantity 'and'? ('area'|'buffer area'|'distance'|'buffer areas')?)+ |'buffer area'|'buffer areas') (('from'|'of'|'to')? (extremaR|extreDist)? (coreC|(networkC (('from'|'for'|'of') origin)? ('to' destination)?)) ('and'|'or')?)+ ;
serviceObj: ((time|quantity) 'and'?)+ 'of'? networkQ (('from'|'for'|'of') origin)? ('to' destination)? ;
//origin: ('from'|'for'|'of')? (extremaR|extreDist)? (objectC|(quantity? grid)) ('of' (objectC|quantity? grid))? ;
//destination: 'to'? DIGIT? (extremaR|extreDist)? objectC;
origin: DIGIT? (extremaR|extreDist)? objectC? 'of'? (objectC|eventC|grid)+ ;
destination: DIGIT? (extremaR|extreDist)? ((objectC|eventC) 'and'?)+;
//boolField: ((quantity 'area'?)|(time 'and'?)+) (('from'|'of')? (extremaR|extreDist)? (coreC|grid))*  ('to' extremaR? coreC)?; //('from'|'of')? extrema? coreC ('from' extrema? (coreC|grid))?
subcon: (coreC compareR quantity)|
        ((topoR|extremaR) (distField|serviceObj))|
        (topoR coreC)|
        (compareR coreC)|
        (distanceR coreC ('of' coreC)?);
aggre: Aggregate ;
topoR: TOPO ;
topoRIn: 'in' (coreC ('of' coreC)?|densityNei);
boolR: Boolean ;
extremaR: Extrema ;
distanceR: Distance ;
extreDist: ExtreDist ;
compareR: Compare ;
quantity: ('equantity' DIGIT) | ('epercent' DIGIT) ;
date: 'edate' DIGIT ;
time: 'etime' DIGIT ;
percent: 'epercent' DIGIT ;
densityNei: quantity ('circle'|'rectangle') ;
distBandNei: 'nearest neighbors' ;
distBand: (quantity 'distance band') | ('distance band' quantity 'by' quantity 'increments') ;
networkC: 'network' DIGIT ;
networkQ: 'networkquality' DIGIT ML ;
objectC: ('object' DIGIT) | ('placename' DIGIT);
eventC: 'event' DIGIT ;
coreC: ('field' DIGIT ML)|('object' DIGIT)|('objectquality' DIGIT ML)|('event' DIGIT)|('eventquality' DIGIT ML)
|('objconamount' DIGIT ML)|('eveconamount' DIGIT ML)|('conamount' DIGIT ML)|('covamount' DIGIT ML)
|('amount' DIGIT)|('objconobjconpro' DIGIT ML)|('eveconobjconpro' DIGIT ML)|('objconobjcovpro' DIGIT ML)|('eveconobjcovpro' DIGIT ML)
|('conconpro' DIGIT ML)|('concovpro' DIGIT ML)|('covpro' DIGIT ML)|('proportion' DIGIT ML);
support : grid | (coreC ('of' coreC)?) | distBand;
extent: ('placename' DIGIT) | 'world';
temEx: 'edate' DIGIT ;


// lexer rules
WH : 'which'|'what'|'from where' ;
Location1 :  'where' ;
Location2 : 'what area'|'what areas' ;
ConAm : 'how many' ;
AUX : 'is'|'are'|'was'|'were' ;
Flase : 'not'|'but not' ;
Aggregate : 'average'|'median'|'total';
TOPO : 'inside'|'located in'|'within'|'covered by'|'away from'|'contain'|'contains'|'touch'|'equal'|'cover'|'intersected with'|'intersects with'|'intersect with'|'overlap with'|'on top of'|'outside'|'affected by';
Boolean : 'have'|'has'|'had'|'visible'|'visible from'|'aged'|'answered by'|'no';
Extrema : 'longest'|'highest'|'biggest'|'most popular'|'fastest'|'most intense'|'minimum'|'maximum'|'maximize'|'fewest';
Distance : 'closest to'|'nearest to' ;
ExtreDist : 'nearest'|'closest';
Compare : 'lower than'|'larger than'|'at least'|'less than'|'more than'|'greater than'|'greater than or equal to'|'smaller than'|'equal to';
ML : 'nominal'|'boolean'|'ordinal'|'interval'|'ratio'|'era'|'ira'|'count'|'loc';
DIGIT: [0-9]+;
WS: [ \n\t\r]+ -> skip;
COMMA: ',' -> skip;
