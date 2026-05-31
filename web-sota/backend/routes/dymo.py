"""Dymo label printer API — TBD: hardware/SDK wiring and production validation not complete."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dymo", tags=["dymo", "TBD"])


class DymoRequest(BaseModel):
    """Base request model for Dymo operations."""


class PrintLabelRequest(DymoRequest):
    """Request model for printing labels."""

    text: str
    tape_size: str = "12mm"  # 6mm, 9mm, 12mm, 19mm, 24mm
    tape_color: str = "black_on_white"  # black_on_white, white_on_black, etc.
    font_size: int = 12
    style: str = "normal"  # normal, bold, italic, underline
    alignment: str = "center"  # left, center, right


class BatchLabelsRequest(DymoRequest):
    """Request model for printing multiple labels."""

    labels: list[str]
    tape_size: str = "12mm"
    tape_color: str = "black_on_white"


class CreateShoppingLabelsRequest(DymoRequest):
    """Request model for creating shopping list labels."""

    items: list[str]
    categories: dict[str, list[str]] | None = None  # Category -> items
    include_checkboxes: bool = True
    tape_size: str = "12mm"


class CreateInventoryLabelsRequest(DymoRequest):
    """Request model for creating inventory labels."""

    items: list[dict[str, str]]  # [{"name": "Item", "location": "Shelf A", "quantity": "5"}]
    include_barcodes: bool = False
    tape_size: str = "19mm"  # Wider for inventory


class LabelTemplateRequest(DymoRequest):
    """Request model for creating custom label templates."""

    template_name: str
    fields: list[dict[str, str]]  # [{"name": "field1", "value": "text", "style": "bold"}]
    layout: str = "horizontal"  # horizontal, vertical, multi_line


class GenerateHumorousLabelsRequest(DymoRequest):
    """Request model for generating and printing humorous fridge labels."""

    theme: str = "random"  # random, dad_jokes, puns, sarcastic, motivational, absurd
    count: int = 50  # Number of labels to generate and print (max 100)
    style: str = "short"  # short, medium, long
    category: str = "general"  # general, food, chores, pets, tech, life
    tape_size: str = "12mm"
    tape_color: str = "black_on_white"


# Mock Dymo printer implementation
class MockDymoPrinter:
    """Mock Dymo printer for development/testing."""

    def __init__(self):
        self.connected = True
        self.tape_sizes = ["6mm", "9mm", "12mm", "19mm", "24mm"]
        self.tape_colors = ["black_on_white", "white_on_black", "red_on_white", "blue_on_white"]

    async def print_label(self, text: str, **kwargs) -> dict:
        """Print a single label."""
        logger.info(f"Dymo: Printing label '{text}' with settings: {kwargs}")
        # In real implementation, this would communicate with Dymo SDK
        return {
            "success": True,
            "label_text": text,
            "settings": kwargs,
            "estimated_length": len(text) * 2,  # Rough estimate in mm
        }

    async def print_batch_labels(self, labels: list[str], **kwargs) -> dict:
        """Print multiple labels."""
        logger.info(f"Dymo: Printing batch of {len(labels)} labels with settings: {kwargs}")
        results = []
        for i, text in enumerate(labels):
            result = await self.print_label(text, **kwargs)
            results.append({**result, "batch_index": i})
        return {"success": True, "total_labels": len(labels), "results": results}

    async def get_status(self) -> dict:
        """Get printer status."""
        return {
            "connected": self.connected,
            "tape_size": "12mm",
            "tape_color": "black_on_white",
            "tape_remaining": 85,  # percentage
            "printer_model": "LabelWriter 450",
            "firmware_version": "1.2.3",
        }

    async def create_shopping_labels(self, items: list[str], **kwargs) -> dict:
        """Create formatted shopping list labels."""
        categories = kwargs.get("categories", {})
        include_checkboxes = kwargs.get("include_checkboxes", True)

        formatted_labels = []
        for item in items:
            checkbox = "☐ " if include_checkboxes else ""
            formatted_labels.append(f"{checkbox}{item}")

        # Add category headers if provided
        if categories:
            categorized_labels = []
            for category, cat_items in categories.items():
                categorized_labels.append(f"--- {category.upper()} ---")
                for item in cat_items:
                    checkbox = "☐ " if include_checkboxes else ""
                    categorized_labels.append(f"{checkbox}{item}")
                categorized_labels.append("")  # Spacer
            formatted_labels = categorized_labels

        return await self.print_batch_labels(formatted_labels, **kwargs)

    async def create_inventory_labels(self, items: list[dict[str, str]], **kwargs) -> dict:
        """Create formatted inventory labels."""
        formatted_labels = []
        for item in items:
            name = item.get("name", "Unknown")
            location = item.get("location", "")
            quantity = item.get("quantity", "")

            if location and quantity:
                label_text = f"{name}\n{location} | Qty: {quantity}"
            elif location:
                label_text = f"{name}\n{location}"
            else:
                label_text = name

            formatted_labels.append(label_text)

        return await self.print_batch_labels(formatted_labels, **kwargs)

    async def create_custom_template(self, template_name: str, fields: list[dict[str, str]], **kwargs) -> dict:
        """Create labels from custom template."""
        formatted_labels = []
        layout = kwargs.get("layout", "horizontal")

        for field_set in fields:
            if layout == "horizontal":
                parts = [f"{name}: {value}" for name, value in field_set.items()]
                label_text = " | ".join(parts)
            elif layout == "vertical":
                parts = [f"{name}: {value}" for name, value in field_set.items()]
                label_text = "\n".join(parts)
            else:  # multi_line
                parts = []
                for name, value in field_set.items():
                    parts.append(f"{name}:")
                    parts.append(value)
                    parts.append("")  # Spacer
                label_text = "\n".join(parts[:-1])  # Remove last spacer

            formatted_labels.append(label_text)

        return await self.print_batch_labels(formatted_labels, **kwargs)

    async def generate_humorous_labels(self, theme: str, count: int, style: str, category: str, **kwargs) -> dict:
        """Generate and print humorous labels for the fridge."""
        # Limit count to prevent abuse
        count = min(count, 100)

        logger.info(f"Dymo: Generating {count} humorous labels (theme: {theme}, category: {category}, style: {style})")

        # Generate humorous texts based on theme and category
        humorous_texts = await self._generate_humorous_texts(theme, count, style, category)

        # Print the batch
        result = await self.print_batch_labels(humorous_texts, **kwargs)

        return {
            **result,
            "theme": theme,
            "category": category,
            "style": style,
            "generated_texts": humorous_texts,
        }

    async def _generate_humorous_texts(self, theme: str, count: int, style: str, category: str) -> list[str]:
        """Generate humorous texts for labels."""
        # Pre-defined humorous texts by category and theme
        humor_templates = {
            "general": {
                "random": [
                    "This is not a drill",
                    "Caution: Contents may be hot",
                    "Property of Sarcasm Inc.",
                    "Do not open until Christmas",
                    "Fragile: Handle with sarcasm",
                    "Warning: May contain nuts",
                    "Keep refrigerated... or else",
                    "Not for human consumption",
                    "Made with love & questionable ingredients",
                    "Best before: Yesterday",
                    "Caution: May cause excessive fun",
                    "Do not try this at home",
                    "Warning: Contents under pressure",
                    "Shake well before opening",
                    "Not responsible for lost socks",
                    "May contain traces of awesome",
                    "Caution: Highly addictive",
                    "Do not feed after midnight",
                    "Warning: May cause spontaneous dancing",
                    "Keep out of reach of children",
                    "Caution: May explode with joy",
                    "Not suitable for boring people",
                    "Warning: May cause excessive laughter",
                    "Do not operate heavy machinery",
                    "Caution: Contents may be radioactive",
                    "Warning: May contain puns",
                    "Keep frozen at all times",
                    "Caution: May cause time travel",
                    "Do not mix with alcohol",
                    "Warning: May cause happiness",
                    "Caution: Highly flammable ego",
                    "Do not open in case of emergency",
                    "Warning: May contain spoilers",
                    "Keep away from magnets",
                    "Caution: May cause addiction",
                    "Do not fold, spindle, or mutilate",
                    "Warning: May cause excessive smiling",
                    "Caution: Contents may be alive",
                    "Do not remove tag under penalty of law",
                    "Warning: May contain nuts (literal)",
                    "Caution: May cause spontaneous combustion",
                    "Do not try this with pets",
                    "Warning: May cause time dilation",
                    "Caution: Highly concentrated awesome",
                    "Do not feed the bears",
                    "Warning: May contain glitter",
                    "Caution: May cause excessive excitement",
                    "Do not operate without supervision",
                    "Warning: May contain traces of genius",
                ],
                "dad_jokes": [
                    "I'm reading a book on anti-gravity. It's impossible to put down!",
                    "Why don't scientists trust atoms? Because they make up everything!",
                    "I told my wife she was drawing her eyebrows too high. She looked surprised!",
                    "Why did the scarecrow win an award? Because he was outstanding in his field!",
                    "I used to play piano by ear, but now I use my hands!",
                    "Why did the bicycle fall over? It was two-tired!",
                    "I'm so good at sleeping, I can do it with my eyes closed!",
                    "Why don't skeletons fight each other? They don't have the guts!",
                    "I told my computer I needed a break, and now it won't stop sending me Kit Kat ads!",
                    "Why did the coffee file a police report? It got mugged!",
                    "I'm reading a book on teleportation. It's bound to take me places!",
                    "Why did the math book look sad? Because it had too many problems!",
                    "I used to be a baker, but I couldn't make enough dough!",
                    "Why did the tomato turn red? Because it saw the salad dressing!",
                    "I'm so good at multitasking, I can waste time, be unproductive, and procrastinate all at once!",
                    "Why did the golfer bring two pairs of pants? In case he got a hole in one!",
                    "I told my wife she was drawing her eyebrows too high. She looked surprised!",
                    "Why don't eggs tell jokes? They'd crack each other up!",
                    "I'm reading a book on anti-gravity. It's impossible to put down!",
                    "Why did the bicycle fall over? It was two-tired!",
                    "I used to be a baker, but I couldn't make enough dough!",
                    "Why did the scarecrow win an award? Because he was outstanding in his field!",
                    "I'm so good at sleeping, I can do it with my eyes closed!",
                    "Why don't scientists trust atoms? Because they make up everything!",
                    "I told my computer I needed a break, and now it won't stop sending me Kit Kat ads!",
                    "Why did the coffee file a police report? It got mugged!",
                    "I'm reading a book on teleportation. It's bound to take me places!",
                    "Why did the math book look sad? Because it had too many problems!",
                    "I used to play piano by ear, but now I use my hands!",
                    "Why don't skeletons fight each other? They don't have the guts!",
                    "Why did the golfer bring two pairs of pants? In case he got a hole in one!",
                    "I told my wife she was drawing her eyebrows too high. She looked surprised!",
                    "Why don't eggs tell jokes? They'd crack each other up!",
                    "I used to be a baker, but I couldn't make enough dough!",
                    "Why did the tomato turn red? Because it saw the salad dressing!",
                    "I'm so good at multitasking, I can waste time, be unproductive, and procrastinate all at once!",
                    "Why did the scarecrow win an award? Because he was outstanding in his field!",
                    "I'm reading a book on anti-gravity. It's impossible to put down!",
                    "Why did the bicycle fall over? It was two-tired!",
                    "I'm so good at sleeping, I can do it with my eyes closed!",
                    "Why don't scientists trust atoms? Because they make up everything!",
                    "I told my computer I needed a break, and now it won't stop sending me Kit Kat ads!",
                    "Why did the coffee file a police report? It got mugged!",
                    "I'm reading a book on teleportation. It's bound to take me places!",
                    "Why did the math book look sad? Because it had too many problems!",
                    "I used to play piano by ear, but now I use my hands!",
                    "Why don't skeletons fight each other? They don't have the guts!",
                ],
                "puns": [
                    "Lettuce turnip the beet",
                    "I'm feeling a bit Claus-trophobic",
                    "That was a mist-ake",
                    "You're snow special",
                    "Olive you so much",
                    "You're the apple of my eye",
                    "I'm feeling grate",
                    "That's snow joke",
                    "You're snow cute",
                    "I'm feeling berry good",
                    "That really floats my boat",
                    "You're the zest",
                    "I'm on a roll",
                    "That's snow way to treat a friend",
                    "You're snow amazing",
                    "I'm feeling souper",
                    "That takes the cake",
                    "You're snow funny",
                    "I'm feeling minty fresh",
                    "That really eggs-cites me",
                    "You're snow cool",
                    "I'm feeling saucy",
                    "That really melts my heart",
                    "You're snow sweet",
                    "I'm feeling chili",
                    "That really blows me away",
                    "You're snow bright",
                    "I'm feeling peachy",
                    "That really tickles my fancy",
                    "You're snow talented",
                    "I'm feeling spicy",
                    "That really rings my bell",
                    "You're snow creative",
                    "I'm feeling cheesy",
                    "That really takes the biscuit",
                    "You're snow artistic",
                    "I'm feeling nutty",
                    "That really knocks my socks off",
                    "You're snow musical",
                    "I'm feeling crabby",
                    "That really floats my goat",
                    "You're snow athletic",
                    "I'm feeling loony",
                    "That really curls my toes",
                    "You're snow smart",
                    "I'm feeling wacky",
                    "That really sets my teeth on edge",
                    "You're snow kind",
                    "I'm feeling bonkers",
                    "That really makes my blood boil",
                ],
            },
            "food": {
                "random": [
                    "Will eat for food",
                    "Nom nom nom",
                    "This cheese is grate",
                    "I'm on a seafood diet. I see food and I eat it.",
                    "Lettuce celebrate with salad",
                    "I'm feeling a bit Claus-trophobic about this fridge",
                    "Do not microwave - may cause spontaneous combustion",
                    "Best before: When pigs fly",
                    "Contains real magic (and some vegetables)",
                    "Made with love and questionable decisions",
                    "Warning: May cause excessive happiness",
                    "Refrigerate after opening (duh)",
                    "Do not consume if seal is broken (or if you're bored)",
                    "May contain nuts (or not, we're not sure)",
                    "Shake well before eating (or don't, your choice)",
                    "Warning: Contents may be hotter than they appear",
                    "Best served cold (or warm, or however you like it)",
                    "Do not feed to children under 3 (or adults over 80)",
                    "Contains gluten (probably)",
                    "Warning: May cause addiction to deliciousness",
                    "Refrigerate or freeze (we don't judge)",
                    "Do not open until ready to eat (or sooner if hungry)",
                    "May contain traces of awesome",
                    "Warning: May explode with flavor",
                    "Best before: Forever (in our hearts)",
                    "Do not microwave if you're impatient",
                    "Contains real fruit (we think)",
                    "Warning: May cause spontaneous dancing",
                    "Refrigerate after opening (seriously this time)",
                    "Do not consume if you're on a diet",
                    "May contain nuts (definitely this time)",
                    "Shake well (but not too hard)",
                    "Warning: Contents may be colder than Antarctica",
                    "Best served with love (and maybe some wine)",
                    "Do not feed to pets (they have their own food)",
                    "May contain traces of genius",
                    "Warning: May cause excessive smiling",
                    "Refrigerate or regret it",
                    "Do not open if you're not hungry",
                    "May contain vegetables (we hope)",
                    "Warning: May cause time travel to flavor town",
                    "Best before: When you finish it",
                    "Do not microwave unless you're brave",
                    "Contains real ingredients",
                    "Warning: May cause spontaneous singing",
                    "Refrigerate and enjoy",
                    "Do not consume if expired (obviously)",
                    "May contain dairy (probably)",
                    "Shake well before judgment",
                    "Warning: Contents may be too delicious",
                    "Best served with friends",
                    "Do not feed to imaginary friends",
                ]
            },
            "chores": {
                "sarcastic": [
                    "Clean me... or don't. I'm not your mom.",
                    "Vacuum me before I become sentient and rebel",
                    "Dust me or I'll haunt your dreams",
                    "Mop me or I'll tell everyone you're lazy",
                    "Clean the bathroom... said no one ever",
                    "Do laundry or wear dirty clothes forever",
                    "Take out trash before it becomes a family member",
                    "Wash dishes or eat off paper plates",
                    "Fold laundry or live in chaos",
                    "Clean windows so you can see the mess outside",
                    "Vacuum carpets before they run away",
                    "Dust shelves or live in a library",
                    "Mop floors or skate on crumbs",
                    "Clean kitchen or order takeout forever",
                    "Do laundry or smell like a gym bag",
                    "Take out recycling before it recycles you",
                    "Wash dishes or attract ants",
                    "Fold laundry or trip over clothes mountains",
                    "Clean bathroom or use outdoor facilities",
                    "Dust furniture or live with dust bunnies",
                    "Mop kitchen or swim in spilled milk",
                    "Clean fridge or grow science experiments",
                    "Do laundry or wear inside out clothes",
                    "Take out compost before it composts you",
                    "Wash dishes or use disposable everything",
                    "Fold laundry or live in wrinkle city",
                    "Clean windows or live in fog",
                    "Dust electronics or short circuit",
                    "Mop bathroom or create slip n slide",
                    "Clean oven or set off smoke alarms",
                    "Do laundry or fade into obscurity",
                    "Take out trash or become a landfill",
                    "Wash dishes or attract roaches",
                    "Fold laundry or look homeless",
                    "Clean microwave or eat burnt food",
                    "Dust blinds or live in shadows",
                    "Mop garage or park in puddles",
                    "Clean basement or live in dungeon",
                    "Do laundry or wear pajamas forever",
                    "Take out garbage or feed raccoons",
                    "Wash dishes or eat with hands",
                    "Fold laundry or live in tent",
                    "Clean attic or store bats",
                    "Dust ceiling or live with spiders",
                    "Mop porch or welcome mosquitoes",
                    "Clean garage or lose your car",
                    "Do laundry or smell like teenager",
                    "Take out recycling or save the planet later",
                    "Wash dishes or lick them clean",
                    "Fold laundry or wear potato sacks",
                    "Clean shed or store regrets",
                    "Dust everything or live in time capsule",
                ]
            },
        }

        # Select appropriate templates based on category and theme
        if category in humor_templates and theme in humor_templates[category]:
            templates = humor_templates[category][theme]
        elif category in humor_templates:
            # Fallback to random if specific theme not found
            templates = humor_templates[category].get("random", humor_templates["general"]["random"])
        else:
            # Ultimate fallback
            templates = humor_templates["general"]["random"]

        # Generate the requested number of texts
        generated_texts = []
        for i in range(count):
            # Cycle through templates if we need more than available
            template_index = i % len(templates)
            text = templates[template_index]

            # Add some variation for medium/long styles
            if style == "medium":
                text = f"{text} ...and other profound thoughts"
            elif style == "long":
                text = f"{text} ...seriously though, think about it. Deep, right?"

            generated_texts.append(text)

        return generated_texts


# Global printer instance
_dymo_printer = MockDymoPrinter()


@router.get("/status")
async def get_dymo_status():
    """Get Dymo printer status."""
    try:
        status = await _dymo_printer.get_status()
        return {"success": True, "status": status}
    except Exception as e:
        logger.exception("Failed to get Dymo status")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/print")
async def print_label(request: PrintLabelRequest):
    """Print a single label."""
    try:
        result = await _dymo_printer.print_label(
            text=request.text,
            tape_size=request.tape_size,
            tape_color=request.tape_color,
            font_size=request.font_size,
            style=request.style,
            alignment=request.alignment,
        )
        return {"success": True, "message": "Label printed successfully", "result": result}
    except Exception as e:
        logger.exception("Failed to print label")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/batch")
async def print_batch_labels(request: BatchLabelsRequest):
    """Print multiple labels."""
    try:
        result = await _dymo_printer.print_batch_labels(
            labels=request.labels, tape_size=request.tape_size, tape_color=request.tape_color
        )
        return {
            "success": True,
            "message": f"Batch of {len(request.labels)} labels printed",
            "result": result,
        }
    except Exception as e:
        logger.exception("Failed to print batch labels")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/shopping")
async def create_shopping_labels(request: CreateShoppingLabelsRequest):
    """Create formatted shopping list labels."""
    try:
        result = await _dymo_printer.create_shopping_labels(
            items=request.items,
            categories=request.categories,
            include_checkboxes=request.include_checkboxes,
            tape_size=request.tape_size,
        )
        return {"success": True, "message": "Shopping labels created and printed", "result": result}
    except Exception as e:
        logger.exception("Failed to create shopping labels")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/inventory")
async def create_inventory_labels(request: CreateInventoryLabelsRequest):
    """Create formatted inventory labels."""
    try:
        result = await _dymo_printer.create_inventory_labels(
            items=request.items,
            include_barcodes=request.include_barcodes,
            tape_size=request.tape_size,
        )
        return {
            "success": True,
            "message": "Inventory labels created and printed",
            "result": result,
        }
    except Exception as e:
        logger.exception("Failed to create inventory labels")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/template")
async def create_custom_template(request: LabelTemplateRequest):
    """Create labels from custom template."""
    try:
        result = await _dymo_printer.create_custom_template(
            template_name=request.template_name, fields=request.fields, layout=request.layout
        )
        return {
            "success": True,
            "message": f"Custom template '{request.template_name}' labels printed",
            "result": result,
        }
    except Exception as e:
        logger.exception("Failed to create custom template labels")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/templates")
async def get_label_templates():
    """Get available label templates."""
    templates = {
        "shopping_basic": {
            "description": "Simple shopping list with checkboxes",
            "example": ["☐ Milk", "☐ Bread", "☐ Eggs"],
        },
        "shopping_categorized": {
            "description": "Categorized shopping list",
            "example": ["--- DAIRY ---", "☐ Milk", "☐ Cheese", "--- BAKERY ---", "☐ Bread"],
        },
        "inventory_simple": {
            "description": "Basic inventory labels",
            "example": ["Item Name\nLocation"],
        },
        "inventory_detailed": {
            "description": "Detailed inventory with quantity",
            "example": ["Widget A\nShelf B-2 | Qty: 15"],
        },
        "address_labels": {
            "description": "Address/contact labels",
            "example": ["John Doe\n123 Main St\nAnytown, ST 12345"],
        },
        "file_folder": {
            "description": "File folder labels",
            "example": ["2024 Tax Documents\nImportant - Keep Safe"],
        },
    }
    return {"success": True, "templates": templates}


@router.get("/tape_sizes")
async def get_tape_sizes():
    """Get available tape sizes."""
    return {
        "success": True,
        "tape_sizes": _dymo_printer.tape_sizes,
        "recommended_uses": {
            "6mm": "Small labels, cable markers",
            "9mm": "General purpose, file tabs",
            "12mm": "Standard labels, addresses",
            "19mm": "Wide labels, inventory, files",
            "24mm": "Extra wide, shipping, large items",
        },
    }


@router.get("/tape_colors")
async def get_tape_colors():
    """Get available tape colors."""
    return {
        "success": True,
        "tape_colors": _dymo_printer.tape_colors,
        "descriptions": {
            "black_on_white": "Classic black text on white tape",
            "white_on_black": "White text on black tape",
            "red_on_white": "Red text on white tape (highlighting)",
            "blue_on_white": "Blue text on white tape (professional)",
        },
    }


@router.post("/humorous-fridge-labels")
async def generate_humorous_labels(request: GenerateHumorousLabelsRequest):
    """Generate and print humorous labels for sticking on the fridge."""
    try:
        # Validate count
        if request.count < 1 or request.count > 100:
            raise HTTPException(status_code=400, detail="Count must be between 1 and 100")

        # Validate theme
        valid_themes = ["random", "dad_jokes", "puns", "sarcastic", "motivational", "absurd"]
        if request.theme not in valid_themes:
            raise HTTPException(status_code=400, detail=f"Theme must be one of: {', '.join(valid_themes)}")

        # Validate category
        valid_categories = ["general", "food", "chores", "pets", "tech", "life"]
        if request.category not in valid_categories:
            raise HTTPException(status_code=400, detail=f"Category must be one of: {', '.join(valid_categories)}")

        result = await _dymo_printer.generate_humorous_labels(
            theme=request.theme,
            count=request.count,
            style=request.style,
            category=request.category,
            tape_size=request.tape_size,
            tape_color=request.tape_color,
        )

        return {
            "success": True,
            "message": f"Generated and printed {request.count} humorous {request.category} labels with {request.theme} theme",
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to generate humorous labels")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/humorous-themes")
async def get_humorous_themes():
    """Get available humorous label themes and categories."""
    return {
        "success": True,
        "themes": {
            "random": "Mix of various humorous styles",
            "dad_jokes": "Classic dad jokes and puns",
            "puns": "Wordplay and clever puns",
            "sarcastic": "Sarcastic and witty remarks",
            "motivational": "Motivational with humor",
            "absurd": "Completely ridiculous and absurd",
        },
        "categories": {
            "general": "General purpose humor",
            "food": "Food-related humor",
            "chores": "Household chores sarcasm",
            "pets": "Pet-related humor",
            "tech": "Technology jokes",
            "life": "Life observations",
        },
        "styles": {
            "short": "One-liners and quick jokes",
            "medium": "Short with a twist",
            "long": "Extended humorous takes",
        },
    }
