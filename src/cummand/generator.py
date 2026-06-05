import random

COLORS = [
    "crimson", "amber", "azure", "coral", "emerald", "indigo", "violet",
    "scarlet", "sapphire", "jade", "rust", "plum", "ochre", "teal",
    "mauve", "slate", "ivory", "lilac", "sienna", "topaz", "auburn",
    "cerulean", "charcoal", "cobalt", "copper", "denim", "fuchsia", "golden",
    "graphite", "hazel", "lavender", "maroon", "midnight", "olive", "pearl",
    "peridot", "rose", "ruby", "salmon", "silver", "tan", "taupe",
    "turquoise", "umber", "vermilion", "wine", "cyan", "magenta", "lime",
    "peach", "mint", "apricot", "bronze", "burgundy", "cardinal", "champagne",
    "cherry", "chestnut", "cinnamon", "cream", "ebony", "garnet", "ginger",
    "heather", "honey", "iris", "khaki", "lemon", "mahogany", "mandarin",
    "mocha", "mustard", "navy", "opal", "orchid", "pastel", "pewter",
    "pistachio", "pumpkin", "quartz", "raisin", "raspberry", "saffron", "sage",
    "smoky", "steel", "stone", "sunset", "tangerine", "thistle", "toffee",
    "tomato", "vanilla", "wheat", "wisteria", "bisque", "celadon", "flaxen",
    "gunmetal", "hematite",
]

ADJECTIVES = [
    "swift", "calm", "brave", "eager", "silent", "bright", "keen",
    "warm", "bold", "cool", "deep", "fair", "fine", "free",
    "full", "glad", "grand", "great", "high", "jolly", "kind",
    "light", "lively", "lucky", "noble", "proud", "pure", "quick",
    "quiet", "rapid", "royal", "safe", "sharp", "shy", "sleek",
    "slim", "smart", "smooth", "solid", "sound", "stable", "still",
    "sweet", "tidy", "tough", "true", "vivid", "wary", "witty",
    "agile", "alert", "astute", "brisk", "chill", "clear", "crisp",
    "droll", "early", "easy", "exact", "faint", "fancy", "fierce",
    "fixed", "fluid", "frank", "fresh", "frosty", "funky", "giant",
    "giddy", "happy", "harsh", "hasty", "heavy", "hollow", "humble",
    "icy", "juicy", "lanky", "lean", "loose", "loud", "loyal",
    "lucid", "lush", "mellow", "merry", "mild", "misty", "neat",
    "nifty", "noisy", "odd", "plain", "polar", "ready", "rich",
    "right", "rigid",
]

ANIMALS = [
    "falcon", "tiger", "otter", "hawk", "wolf", "lynx", "puma",
    "egret", "crane", "swan", "heron", "raven", "crow", "dove",
    "finch", "robin", "eagle", "owl", "stork", "koala", "panda",
    "sloth", "marten", "sable", "badger", "weasel", "ferret", "mink",
    "beaver", "tapir", "zebra", "okapi", "giraffe", "camel", "llama",
    "alpaca", "deer", "moose", "elk", "bison", "yak", "gazelle",
    "antelope", "impala", "buffalo", "cheetah", "leopard", "jaguar", "panther",
    "cougar", "caracal", "serval", "ocelot", "bobcat", "mongoose", "meerkat",
    "hyena", "fox", "coyote", "jackal", "dingo", "raccoon", "coati",
    "monkey", "baboon", "macaque", "lemur", "loris", "dolphin", "whale",
    "porpoise", "orca", "walrus", "seal", "penguin", "puffin", "albatross",
    "pelican", "cormorant", "gannet", "booby", "gull", "tern", "woodpecker",
    "kingfisher", "toucan", "parrot", "macaw", "cockatoo", "canary", "sparrow",
    "wren", "thrush", "oriole", "cardinal", "butterfly", "dragonfly", "grasshopper",
    "ladybug", "firefly",
]

NOUNS = [
    "river", "forest", "summit", "valley", "meadow", "canyon", "ridge",
    "basin", "delta", "dune", "fjord", "glade", "grove", "island",
    "lagoon", "mesa", "mound", "oasis", "peak", "plain", "plateau",
    "prairie", "rapids", "reef", "steppe", "stream", "swamp", "tundra",
    "waterfall", "woodland", "arch", "avenue", "banner", "bastion", "beacon",
    "bridge", "castle", "chapel", "citadel", "column", "crystal", "dagger",
    "domain", "empire", "fable", "fossil", "galaxy", "garden", "gem",
    "guild", "harbor", "haven", "horizon", "jungle", "kingdom", "knight",
    "lantern", "legend", "lighthouse", "lotus", "marble", "mirror", "monument",
    "mystic", "nexus", "oracle", "palace", "panorama", "passage", "pearl",
    "phoenix", "pillar", "portal", "quest", "realm", "relic", "ruins",
    "saga", "scroll", "season", "shrine", "signal", "sphere", "spirit",
    "statue", "temple", "throne", "tide", "titan", "tower", "trail",
    "treasure", "vault", "vista", "vortex", "voyage", "whisper", "wisdom",
    "wonder", "zephyr",
]


def generate_code() -> str:
    color = random.choice(COLORS)
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    noun = random.choice(NOUNS)
    return f"{color}-{adj}-{animal}-{noun}"


def validate_code(code: str) -> bool:
    parts = code.split("-")
    if len(parts) != 4:
        return False
    color, adj, animal, noun = parts
    return (color in COLORS and adj in ADJECTIVES
            and animal in ANIMALS and noun in NOUNS)
