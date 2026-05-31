import logging

logger = logging.getLogger(__name__)

"""
Extract Robot Designs from Anime in Plex

Searches Sandra's 50,000 anime episode collection for robot/mecha anime,
extracts design information for virtual robotics (vrobs) testing.

**Timestamp**: 2025-12-02
**Purpose**: Build anime vrob catalog for Unity3D/VRChat testing
**Resource**: Plex server on Goliath (50,000 anime episodes)
"""

import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from plexapi.server import PlexServer


class EmotionType(StrEnum):
    """Vrob emotion spectrum (0-10 scale)"""

    TERRIFYING = "0-2"  # Evangelion, Zearth, Genocyber
    INTIMIDATING = "3-4"  # Military, Terminator
    NEUTRAL = "5-6"  # Scout, worker mechs
    FRIENDLY = "7-8"  # R2-D2, Tachikomas, WALL-E
    EXTREMELY_CUTE = "9-10"  # Astro Boy, Chii, Doraemon


@dataclass
class AnimeRobotDesign:
    """Anime robot design documentation"""

    id: str
    name: str
    series: str
    year: int
    height_cm: float
    emotion_score: float  # 0=terrifying, 10=cute
    aesthetic: str  # "organic", "mechanical", "bio-mecha", etc.
    mobility: str  # "wheels", "legs", "tracks", "hover", "flight"
    features: list[str]
    partner_acceptance: str  # "very_low", "low", "medium", "high", "very_high"
    benny_reaction: str  # "terrified", "alert", "curious", "friendly"
    model_available: bool
    model_source: str  # URL or "need_to_create"
    scale_factor: float  # For Unity (relative to Scout 11.5cm)
    notes: str


# Famous robot anime database
FAMOUS_ROBOT_ANIME = {
    # Classic Era (1960s-1980s)
    "astro_boy": {
        "title": "Astro Boy",
        "japanese": "Tetsuwan Atom",
        "year": 1963,
        "robots": ["Astro Boy", "Uran", "Atlas", "Professor Ochanomizu's creations"],
    },
    "gigantor": {
        "title": "Gigantor",
        "japanese": "Tetsujin 28-go",
        "year": 1963,
        "robots": ["Gigantor (remote-controlled mecha)"],
    },
    "mazinger_z": {
        "title": "Mazinger Z",
        "japanese": "Majinga Zetto",
        "year": 1972,
        "robots": ["Mazinger Z", "Great Mazinger", "Mechanical Beasts"],
    },
    "mobile_suit_gundam": {
        "title": "Mobile Suit Gundam",
        "japanese": "Kido Senshi Gundam",
        "year": 1979,
        "robots": ["RX-78-2 Gundam", "Zaku II", "countless mobile suits"],
    },
    # Golden Age (1990s-2000s)
    "evangelion": {
        "title": "Neon Genesis Evangelion",
        "japanese": "Shin Seiki Evangelion",
        "year": 1995,
        "robots": ["EVA Unit-01", "Unit-00", "Unit-02", "Angels (biomechanical)"],
        "emotion": "terrifying",
        "notes": "Biomechanical horror, psychological darkness",
    },
    "ghost_in_shell": {
        "title": "Ghost in the Shell: Stand Alone Complex",
        "japanese": "Koukaku Kidoutai",
        "year": 2002,
        "robots": ["Tachikomas (spider tanks)", "Motoko's cyborg body", "Think tanks"],
        "emotion": "friendly",
        "notes": "Cute AI in weapon platforms",
    },
    "chobits": {
        "title": "Chobits",
        "japanese": "Chobittsu",
        "year": 2002,
        "robots": ["Chii", "Sumomo", "Kotoko", "persocoms"],
        "emotion": "extremely_cute",
        "notes": "Human-like androids, innocent aesthetic",
    },
    "patlabor": {
        "title": "Mobile Police Patlabor",
        "japanese": "Kido Keisatsu Patoreibaa",
        "year": 1988,
        "robots": ["Ingram", "police labors", "construction mechs"],
        "emotion": "neutral",
        "notes": "Realistic working robots",
    },
    # Modern Era (2010s-2020s)
    "bokurano": {
        "title": "Bokurano",
        "japanese": "Bokura no",
        "year": 2007,
        "creator": "Mahiro Kitoh",
        "robots": ["Zearth (dark mecha)", "enemy mechs"],
        "emotion": "terrifying",
        "notes": "Existential horror, beautiful but ominous, pilots die",
    },
    "code_geass": {
        "title": "Code Geass",
        "japanese": "Kodo Giasu",
        "year": 2006,
        "robots": ["Knightmare Frames", "Lancelot", "Guren"],
        "emotion": "neutral",
        "notes": "Military mechs with personality",
    },
    "darling_franxx": {
        "title": "Darling in the FranXX",
        "japanese": "Darling in the FranXX",
        "year": 2018,
        "robots": ["FranXX mechs", "Strelizia", "biological mechs"],
        "emotion": "friendly",
        "notes": "Organic-mechanical hybrids",
    },
}


class PlexAnimeRobotExtractor:
    """Extract robot designs from Plex anime collection"""

    def __init__(self, plex_url: str = "http://goliath:32400", token: str | None = None):
        self.plex = PlexServer(plex_url, token)
        self.anime_library = self.plex.library.section("Anime")
        self.robot_designs = []

    def find_robot_anime(self) -> list:
        """
        Search Plex for anime with robot/mecha content.

        Returns:
            List of anime shows with robots
        """
        # Search by Mecha genre
        mecha_anime = self.anime_library.search(filters={"genre": "Mecha"})

        # Search by keywords
        keywords = [
            "robot",
            "mecha",
            "android",
            "cyborg",
            "gundam",
            "mazinger",
            "astro",
            "evangelion",
            "mobile suit",
            "labor",
            "frame",
            "unit",
        ]

        keyword_results = []
        for keyword in keywords:
            try:
                results = self.anime_library.search(title=keyword)
                keyword_results.extend(results)
            except Exception as e:
                logger.info(f"Search failed for '{keyword}': {e}")

        # Combine and deduplicate
        all_results = {show.title: show for show in (mecha_anime + keyword_results)}

        logger.info(f"Found {len(all_results)} anime with robot content!")
        return sorted(all_results.values(), key=lambda x: x.title)

    def extract_design_from_anime(self, anime_title: str) -> list[AnimeRobotDesign]:
        """
        Extract robot designs from specific anime.

        Manual for now - requires watching/analyzing episodes.
        Future: AI vision analysis of episodes.

        Returns:
            List of robot designs found in anime
        """
        # Check if anime is in famous database
        for _key, data in FAMOUS_ROBOT_ANIME.items():
            if anime_title.lower() in data["title"].lower():
                logger.info(f"Found famous anime: {data['title']}")
                return self._extract_famous_designs(data)

        logger.info(f"Anime '{anime_title}' not in famous database - manual extraction needed")
        return []

    def _extract_famous_designs(self, anime_data: dict) -> list[AnimeRobotDesign]:
        """Extract pre-documented famous robot designs"""
        designs = []

        # Example: Astro Boy
        if "Astro Boy" in anime_data["title"]:
            designs.append(
                AnimeRobotDesign(
                    id="astro_boy_001",
                    name="Astro Boy (Mighty Atom)",
                    series=anime_data["title"],
                    year=anime_data["year"],
                    height_cm=135.0,
                    emotion_score=9.5,  # Extremely cute
                    aesthetic="retro_heroic",
                    mobility="flight",
                    features=["jet_boots", "arm_cannons", "super_strength", "kind_heart"],
                    partner_acceptance="very_high",
                    benny_reaction="curious",
                    model_available=False,
                    model_source="https://sketchfab.com/search?q=astro+boy",
                    scale_factor=135.0 / 11.5,  # 11.74× Scout size
                    notes="Iconic first anime robot, universally loved, nostalgic",
                )
            )

        # Example: Tachikoma (Ghost in the Shell)
        if "Ghost in the Shell" in anime_data["title"]:
            designs.append(
                AnimeRobotDesign(
                    id="tachikoma_001",
                    name="Tachikoma",
                    series=anime_data["title"],
                    year=anime_data["year"],
                    height_cm=240.0,
                    emotion_score=7.5,  # Cute but military
                    aesthetic="organic_mechanical",
                    mobility="quadruped_spider",
                    features=[
                        "AI_personality",
                        "thermoptic_camo",
                        "spider_climb",
                        "childlike_speech",
                    ],
                    partner_acceptance="high",
                    benny_reaction="alert",
                    model_available=False,
                    model_source="need_to_create",
                    scale_factor=240.0 / 11.5,  # 20.87× Scout size
                    notes="Friendly AI in weapon platform - cute spider tank",
                )
            )

        # Example: Zearth (Bokurano - Mahiro Kitoh)
        if "Bokurano" in anime_data.get("title", ""):
            designs.append(
                AnimeRobotDesign(
                    id="zearth_bokurano_001",
                    name="Zearth",
                    series=f"{anime_data['title']} (Mahiro Kitoh)",
                    year=anime_data["year"],
                    height_cm=50000.0,  # 500m! Scale to 500cm for apartment
                    emotion_score=1.0,  # Existential horror
                    aesthetic="dark_minimalist",
                    mobility="bipedal",
                    features=[
                        "reality_manipulation",
                        "pilot_cockpit",
                        "existential_dread",
                        "beautiful_horror",
                    ],
                    partner_acceptance="very_low",
                    benny_reaction="terrified",
                    model_available=False,
                    model_source="need_to_create",
                    scale_factor=500.0 / 11.5,  # 43.48× Scout for 5m test version
                    notes="Mahiro Kitoh's dark masterpiece - beautiful but ominous, test aesthetic limit",
                )
            )

        return designs

    def generate_vrob_catalog(self, output_file: str = "anime_vrob_catalog.json"):
        """
        Generate complete vrob catalog from Plex collection.

        Args:
            output_file: JSON output filename

        Returns:
            Catalog dict with all extracted designs
        """
        catalog = {
            "catalog_version": "1.0",
            "generated": "2025-12-02",
            "source": "Sandra's Plex Collection (50,000 anime episodes)",
            "total_anime_searched": 0,
            "total_robots_found": 0,
            "robots": [],
        }

        # Search for robot anime
        robot_anime = self.find_robot_anime()
        catalog["total_anime_searched"] = len(robot_anime)

        # Extract designs from famous anime
        for anime in robot_anime[:20]:  # Start with top 20
            try:
                designs = self.extract_design_from_anime(anime.title)
                for design in designs:
                    catalog["robots"].append(asdict(design))
            except Exception as e:
                logger.info(f"Failed to extract from {anime.title}: {e}")

        catalog["total_robots_found"] = len(catalog["robots"])

        # Save catalog
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(catalog['robots'])} vrob designs to {output_file}")
        return catalog


def main():
    """
    Main extraction workflow.

    Usage:
        python extract_anime_vrobs.py
    """
    # Initialize extractor (update with your Plex token)
    extractor = PlexAnimeRobotExtractor(plex_url="http://goliath:32400", token="YOUR_PLEX_TOKEN_HERE")

    # Find all robot anime
    logger.info("Searching Plex for robot anime...")
    robot_anime = extractor.find_robot_anime()

    logger.info(f"\nFound {len(robot_anime)} anime with robot content:")
    for i, anime in enumerate(robot_anime[:10], 1):
        logger.info(f"{i}. {anime.title} ({anime.year})")

    # Generate vrob catalog
    logger.info("\nExtracting robot designs...")
    catalog = extractor.generate_vrob_catalog()

    logger.info("\n✅ Catalog complete!")
    logger.info(f"   - Total anime: {catalog['total_anime_searched']}")
    logger.info(f"   - Total robots: {catalog['total_robots_found']}")
    logger.info("   - Output: anime_vrob_catalog.json")

    # Print emotion distribution
    emotions = {}
    for robot in catalog["robots"]:
        score = robot["emotion_score"]
        category = "cute" if score >= 7 else "neutral" if score >= 4 else "scary"
        emotions[category] = emotions.get(category, 0) + 1

    logger.info("\n📊 Emotion Distribution:")
    logger.info(f"   - Cute (7-10): {emotions.get('cute', 0)}")
    logger.info(f"   - Neutral (4-6): {emotions.get('neutral', 0)}")
    logger.info(f"   - Scary (0-3): {emotions.get('scary', 0)}")


if __name__ == "__main__":
    main()
