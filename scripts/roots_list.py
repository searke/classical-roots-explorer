"""A hand-made list of well-known Latin and Greek roots, with their usual English spellings.

Wiktionary's word breakdowns cover prefixes and combining forms well (tele-, -graph, bio-),
but Latin verb stems such as dict, ject or struct rarely appear as separate pieces. This list
fills that gap. A word is only matched to one of these roots when its own Wiktionary etymology
confirms it (predict ← Latin praedīcō), so a spelling coincidence is not enough.

Three-letter spellings that collide with unrelated words (mar "sea" vs marble, sal "leap" vs
salad) are left out on purpose; the longer spellings still catch most words.

Format: one root per line — spellings separated by spaces | origin (L or G) | meaning.
"""

ROOTS_TEXT = """
dict dic dict | L | say, speak
duc duct duce | L | lead
ject jac | L | throw
struct stru | L | build
scrib script | L | write
spec spect spic | L | look, see
vis vid | L | see
port | L | carry
mit miss mis | L | send
fer | L | carry, bring
pon pos posit pose pound | L | put, place
cap capt cept cip ceive ceit | L | take, seize
fac fact fect fic | L | make, do
cred | L | believe
flect flex | L | bend
junct join | L | join
rupt | L | break
ten tin tain tent | L | hold
vert vers | L | turn
voc vok | L | call, voice
aud | L | hear
bene | L | well, good
corp | L | body
curs cour | L | run
fid | L | trust, faith
form | L | shape
grad gress | L | step, go
jud | L | judge
leg lect | L | read, choose, law
loc | L | place
luc lum | L | light
man manu | L | hand
mater matr | L | mother
pater patr | L | father
mort | L | death
mov mot mob | L | move
nasc | L | born
nov | L | new
pel puls | L | drive, push
pend pens | L | hang, weigh
plic plex ply | L | fold
publ | L | people
prim | L | first
quer quest quir quis | L | ask, seek
sens sent | L | feel
sequ secu | L | follow
sign | L | mark, sign
spir | L | breathe
stat stit sist | L | stand
tang tact ting | L | touch
temp | L | time
terr | L | earth
tort | L | twist
tract | L | pull, drag
trib | L | give, allot
turb | L | disturb, stir
ven vent | L | come
vit viv | L | life, live
vol | L | wish, will
vor | L | eat
cede ceed cess | L | go, yield
clud clus clos | L | shut
cid cis | L | cut, kill
fin | L | end, limit
flu flux | L | flow
frag fract | L | break
gest | L | carry, bear
greg | L | flock, gather
hab hib | L | have, hold
liber | L | free
loqu locu | L | speak
magn | L | great
ment | L | mind
migr | L | move, wander
monit | L | warn, remind
mut | L | change
noc nox | L | harm
nomin | L | name
nunc | L | announce
oper | L | work
pac | L | peace
part | L | part
pass | L | suffer, feel
plaud plaus | L | clap
plen plet | L | full
press | L | press
punct pung | L | point, prick
rect reg | L | straight, rule
rog | L | ask
sacr sanct | L | holy
sil | L | leap
scend | L | climb
sect seg | L | cut
sed sid sess | L | sit
serv | L | serve, keep
solv solu | L | loosen
spond spons | L | promise, answer
string strict | L | bind, tighten
sump | L | take
tend tens | L | stretch
tex | L | weave
tox | G | poison
urb | L | city
vac | L | empty
val | L | strong, worth
vinc vict | L | conquer
vest | L | clothe
volv volu | L | roll, turn
cord | L | heart
carn | L | flesh
cent | L | hundred
mill | L | thousand
duo | L | two
equ | L | equal
grat | L | pleasing, thanks
grav | L | heavy
alter | L | other
anim | L | life, mind
aqu | L | water
cand | L | glow, white
capit | L | head
civ | L | citizen
dent | L | tooth
dom | L | house, master
fort | L | strong
frat | L | brother
lingu | L | tongue
lumin | L | light
mens | L | measure
ocul | L | eye
ped | L | foot
pug | L | fight
simil simul | L | like
umbr | L | shade
verb | L | word
anthrop | G | human
arch | G | rule, chief
chron | G | time
crac crat | G | rule
dem | G | people
gam | G | marriage
gen | G | birth, kind
geo | G | earth
gno | G | know
gon | G | angle
gram graph | G | write, draw
hydr | G | water
kine cine | G | movement
log | G | word, study
morph | G | shape
nom | G | law, arrange
onym | G | name
path | G | feeling, disease
paed paedo | G | child
phil | G | love
phon | G | sound
phot | G | light
pol | G | city
psych | G | mind
scop | G | look
soph | G | wise
tele | G | far
theo | G | god
therm | G | heat
top | G | place
zoo | G | animal
"""


# Assimilated spellings of one prefix (ad- becomes ac-, af-, ap-… before some consonants).
PREFIX_FAMILIES = {
    "ad": "ac af ag al ap ar as at",
    "in": "il im ir",
    "con": "co col com cor",
    "ob": "oc of op",
    "ex": "e ef",
    "syn": "sy syl sym",
    "dis": "di dif",
    "sub": "suc suf sug sup sur sus",
}


def load():
    roots = []
    for line in ROOTS_TEXT.strip().splitlines():
        spellings, origin, meaning = [x.strip() for x in line.split("|")]
        roots.append({"spellings": spellings.split(), "origin": "Latin" if origin == "L" else "Greek",
                      "meaning": meaning})
    return roots
