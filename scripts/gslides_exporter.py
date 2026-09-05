"""
Google Slides API Batch Serializer
Converts MT Deck IR to Google Slides REST API batchUpdate requests.
"""

from typing import Dict, Any, List, Tuple
import uuid


PT_TO_EMU = 12700  # 1 point = 12,700 EMUs (English Metric Units)
INCH_TO_EMU = 914400  # 1 inch = 914,400 EMUs


class GoogleSlidesColor:
    """Google Slides color palette matching MT theme."""

    @staticmethod
    def rgb_to_gslides(r: int, g: int, b: int) -> Dict[str, Any]:
        """Convert 0-255 RGB to Google Slides 0.0-1.0 float format."""
        return {
            "red": r / 255.0,
            "green": g / 255.0,
            "blue": b / 255.0
        }


# Define color constants after class definition
GoogleSlidesColor.NAVY = GoogleSlidesColor.rgb_to_gslides(13, 27, 42)  # #0D1B2A
GoogleSlidesColor.TEAL = GoogleSlidesColor.rgb_to_gslides(42, 157, 176)  # #2A9DB0
GoogleSlidesColor.RED = GoogleSlidesColor.rgb_to_gslides(230, 57, 70)  # #E63946
GoogleSlidesColor.GREEN = GoogleSlidesColor.rgb_to_gslides(42, 157, 126)  # #2A9D7E
GoogleSlidesColor.ORANGE = GoogleSlidesColor.rgb_to_gslides(247, 162, 97)  # #F7A261
GoogleSlidesColor.WHITE = GoogleSlidesColor.rgb_to_gslides(255, 255, 255)
GoogleSlidesColor.LIGHT_GREY = GoogleSlidesColor.rgb_to_gslides(240, 240, 240)


class GoogleSlidesBatchBuilder:
    """Builds Google Slides batchUpdate API request payload."""

    def __init__(self, presentation_id: str = None):
        """Initialize builder with optional presentation ID."""
        self.presentation_id = presentation_id or str(uuid.uuid4())
        self.requests: List[Dict[str, Any]] = []
        self.shape_counter = 0

    def _gen_object_id(self, prefix: str = "obj") -> str:
        """Generate unique object ID for shapes and elements."""
        self.shape_counter += 1
        return f"{prefix}_{self.shape_counter}_{uuid.uuid4().hex[:8]}"

    def add_create_slide(self, slide_object_id: str, insertion_index: int) -> str:
        """Add request to create a new blank slide."""
        self.requests.append({
            "createSlide": {
                "objectId": slide_object_id,
                "insertionIndex": insertion_index,
                "slideLayout": {"predefinedLayout": "BLANK"}
            }
        })
        return slide_object_id

    def add_background_color(self, slide_id: str, hex_color: str):
        """Add request to set slide background color."""
        rgb = self._hex_to_rgb(hex_color)
        self.requests.append({
            "updateSlideProperties": {
                "objectId": slide_id,
                "fields": "pageProperties.pageBackgroundFill.solidFill.color",
                "slideProperties": {
                    "pageProperties": {
                        "pageBackgroundFill": {
                            "solidFill": {
                                "color": {"rgbColor": rgb}
                            }
                        }
                    }
                }
            }
        })

    def add_shape(
        self,
        slide_id: str,
        shape_id: str,
        shape_type: str,
        left_inches: float,
        top_inches: float,
        width_inches: float,
        height_inches: float,
        bg_hex: str = "#FFFFFF",
        border_hex: str = None,
        border_width_pt: float = 0
    ):
        """Add request to create a shape (rectangle, circle, etc.)."""
        left_emu = int(left_inches * INCH_TO_EMU)
        top_emu = int(top_inches * INCH_TO_EMU)
        width_emu = int(width_inches * INCH_TO_EMU)
        height_emu = int(height_inches * INCH_TO_EMU)

        # Create shape
        self.requests.append({
            "createShape": {
                "objectId": shape_id,
                "shapeType": shape_type,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width_emu, "unit": "EMU"},
                        "height": {"magnitude": height_emu, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": left_emu,
                        "translateY": top_emu,
                        "unit": "EMU"
                    }
                }
            }
        })

        # Update background fill
        bg_rgb = self._hex_to_rgb(bg_hex)
        self.requests.append({
            "updateShapeProperties": {
                "objectId": shape_id,
                "fields": "shapeBackgroundFill.solidFill.color",
                "shapeProperties": {
                    "shapeBackgroundFill": {
                        "solidFill": {
                            "color": {"rgbColor": bg_rgb}
                        }
                    }
                }
            }
        })

        # Add border if specified
        if border_hex and border_width_pt > 0:
            border_rgb = self._hex_to_rgb(border_hex)
            self.requests.append({
                "updateShapeProperties": {
                    "objectId": shape_id,
                    "fields": "outline.outlineFill.solidFill.color,outline.weight",
                    "shapeProperties": {
                        "outline": {
                            "outlineFill": {
                                "solidFill": {
                                    "color": {"rgbColor": border_rgb}
                                }
                            },
                            "weight": {
                                "magnitude": int(border_width_pt * PT_TO_EMU),
                                "unit": "EMU"
                            }
                        }
                    }
                }
            })

    def add_text_box(
        self,
        slide_id: str,
        text_box_id: str,
        left_inches: float,
        top_inches: float,
        width_inches: float,
        height_inches: float,
        text: str,
        font_size_pt: int = 12,
        bold: bool = False,
        color_hex: str = "#FFFFFF",
        alignment: str = "START"
    ):
        """Add request to create text box with formatted text."""
        # Create shape (rectangle as text box container)
        self.add_shape(
            slide_id,
            text_box_id,
            "RECTANGLE",
            left_inches,
            top_inches,
            width_inches,
            height_inches,
            bg_hex="#00000000",  # Transparent
            border_hex=None
        )

        # Insert text
        self.requests.append({
            "insertText": {
                "objectId": text_box_id,
                "insertionIndex": 0,
                "text": text
            }
        })

        # Format text
        text_color_rgb = self._hex_to_rgb(color_hex)
        self.requests.append({
            "updateTextStyle": {
                "objectId": text_box_id,
                "fields": "fontSize,bold,foregroundColor",
                "style": {
                    "bold": bold,
                    "fontSize": {
                        "magnitude": font_size_pt,
                        "unit": "PT"
                    },
                    "foregroundColor": {
                        "opaqueColor": {
                            "rgbColor": text_color_rgb
                        }
                    }
                },
                "textRange": {"type": "ALL"}
            }
        })

    def add_table(
        self,
        slide_id: str,
        table_id: str,
        left_inches: float,
        top_inches: float,
        rows: int,
        columns: int,
        row_height_inches: float = 0.4,
        col_width_inches: float = 2.0
    ):
        """Add request to create table."""
        left_emu = int(left_inches * INCH_TO_EMU)
        top_emu = int(top_inches * INCH_TO_EMU)
        row_height_emu = int(row_height_inches * INCH_TO_EMU)
        col_width_emu = int(col_width_inches * INCH_TO_EMU)

        # Table dimensions
        table_width_emu = col_width_emu * columns
        table_height_emu = row_height_emu * rows

        self.requests.append({
            "createTable": {
                "objectId": table_id,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": table_width_emu, "unit": "EMU"},
                        "height": {"magnitude": table_height_emu, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": left_emu,
                        "translateY": top_emu,
                        "unit": "EMU"
                    }
                },
                "rows": rows,
                "columns": columns
            }
        })

    def build_payload(self) -> Dict[str, Any]:
        """Return the complete batchUpdate request payload."""
        return {
            "requests": self.requests
        }

    @staticmethod
    def _hex_to_rgb(hex_str: str) -> Dict[str, float]:
        """Convert #RRGGBB to Google Slides RGBColor (0.0-1.0 range)."""
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 8:  # Handle RGBA format by stripping alpha
            hex_str = hex_str[:6]
        return {
            "red": int(hex_str[0:2], 16) / 255.0,
            "green": int(hex_str[2:4], 16) / 255.0,
            "blue": int(hex_str[4:6], 16) / 255.0
        }


def build_gslides_batch_from_ir(deck_ir: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate MT Deck IR into Google Slides batchUpdate payload.

    Args:
        deck_ir: Intermediate representation dict from mt_deck_ir.build_deck_ir()

    Returns:
        Google Slides API batchUpdate payload ready for REST API call
    """
    builder = GoogleSlidesBatchBuilder()

    # Process each slide
    for slide_def in deck_ir.get("slides", []):
        slide_id = slide_def.get("slide_id", f"slide_{slide_def.get('slide_number', 1)}")

        # Create slide
        builder.add_create_slide(slide_id, slide_def.get("slide_number", 1) - 1)

        # Add background (dark navy)
        builder.add_background_color(slide_id, "#0D1B2A")

        # Add title
        title = slide_def.get("title", "")
        if title:
            title_id = builder._gen_object_id("title")
            builder.add_text_box(
                slide_id,
                title_id,
                left_inches=0.5,
                top_inches=0.3,
                width_inches=9.0,
                height_inches=0.6,
                text=title,
                font_size_pt=32,
                bold=True,
                color_hex="#FFFFFF"
            )

        # Render slide-specific content based on layout type
        layout_type = slide_def.get("layout_type", "")
        elements = slide_def.get("elements", {})

        if layout_type == "kpi_grid":
            _render_kpi_grid(builder, slide_id, elements)
        elif layout_type == "waterfall_bridge":
            _render_waterfall(builder, slide_id, elements)
        elif layout_type == "scatter_matrix":
            _render_matrix(builder, slide_id, elements)
        elif layout_type == "action_register":
            _render_action_register(builder, slide_id, elements)
        elif layout_type == "comparison_table":
            _render_comparison_table(builder, slide_id, elements)

    return builder.build_payload()


def _render_kpi_grid(builder: GoogleSlidesBatchBuilder, slide_id: str, elements: Dict[str, Any]):
    """Render KPI cards grid on slide."""
    kpi_cards = elements.get("kpi_cards", [])
    for idx, card in enumerate(kpi_cards):
        left = 0.5 + (idx * 2.25)
        top = 1.2

        # KPI card box
        card_id = builder._gen_object_id("kpi")
        builder.add_shape(
            slide_id, card_id, "RECTANGLE",
            left, top, 2.0, 1.2,
            bg_hex="#1F2D46",
            border_hex="#2A9DB0",
            border_width_pt=2
        )

        # Value
        value_id = builder._gen_object_id("value")
        builder.add_text_box(
            slide_id, value_id,
            left + 0.1, top + 0.2, 1.8, 0.5,
            text=card.get("value", "–"),
            font_size_pt=18,
            bold=True,
            color_hex="#2A9DB0"
        )

        # Label
        label_id = builder._gen_object_id("label")
        builder.add_text_box(
            slide_id, label_id,
            left + 0.1, top + 0.7, 1.8, 0.4,
            text=card.get("label", ""),
            font_size_pt=10,
            bold=True,
            color_hex="#FFFFFF"
        )


def _render_waterfall(builder: GoogleSlidesBatchBuilder, slide_id: str, elements: Dict[str, Any]):
    """Render waterfall diagnostic on slide."""
    bridge = elements.get("bridge", {})
    chain_name = elements.get("chain_name", "Reliance")

    # Waterfall steps
    steps = [
        ("Dispatched", f"₹{bridge.get('primary', 0):.2f} Cr", "#2A9DB0"),
        ("Shelf Loss", f"−₹{bridge.get('shelf_loss', 0):.2f} Cr", "#E63946"),
        ("Price Loss", f"−₹{bridge.get('price_loss', 0):.2f} Cr", "#E63946"),
        ("Stuck NPI", f"−₹{bridge.get('stuck_inventory', 0):.2f} Cr", "#E63946"),
        ("Realized", f"₹{bridge.get('realized_offtake', 0):.2f} Cr", "#2A9D7E"),
    ]

    for idx, (title, value, color) in enumerate(steps):
        left = 0.5 + (idx * 1.8)
        top = 1.5

        # Card
        card_id = builder._gen_object_id("waterfall")
        builder.add_shape(
            slide_id, card_id, "RECTANGLE",
            left, top, 1.6, 1.5,
            bg_hex="#1F2D46",
            border_hex=color,
            border_width_pt=2
        )

        # Value
        val_id = builder._gen_object_id("wf_val")
        builder.add_text_box(
            slide_id, val_id,
            left + 0.1, top + 0.3, 1.4, 0.5,
            text=value,
            font_size_pt=14,
            bold=True,
            color_hex=color
        )

        # Title
        title_id = builder._gen_object_id("wf_title")
        builder.add_text_box(
            slide_id, title_id,
            left + 0.1, top + 0.8, 1.4, 0.4,
            text=title,
            font_size_pt=9,
            bold=True,
            color_hex="#FFFFFF"
        )


def _render_matrix(builder: GoogleSlidesBatchBuilder, slide_id: str, elements: Dict[str, Any]):
    """Render 2x2 risk-opportunity matrix on slide."""
    zones = elements.get("zones", [])

    for zone in zones:
        x_coord = zone.get("x_coord", 2.0)
        y_coord = zone.get("y_coord", 3.0)

        color_map = {
            "RED": "#E63946",
            "ORANGE": "#F7A261",
            "GREEN": "#2A9D7E",
            "YELLOW": "#C8A032"
        }
        color = color_map.get(zone.get("color_theme", "GREEN"), "#2A9D7E")

        # Zone bubble
        bubble_id = builder._gen_object_id("zone")
        builder.add_shape(
            slide_id, bubble_id, "OVAL",
            x_coord - 0.4, y_coord - 0.2, 0.8, 0.4,
            bg_hex="#1F2D46",
            border_hex=color,
            border_width_pt=2
        )

        # Zone label
        label_id = builder._gen_object_id("zone_label")
        builder.add_text_box(
            slide_id, label_id,
            x_coord - 0.4, y_coord - 0.2, 0.8, 0.4,
            text=f"{zone.get('name', 'Zone')}\n{zone.get('conversion', 0):.0f}%",
            font_size_pt=8,
            bold=True,
            color_hex=color
        )


def _render_action_register(builder: GoogleSlidesBatchBuilder, slide_id: str, elements: Dict[str, Any]):
    """Render action register table on slide."""
    actions = elements.get("actions", [])

    # Table with 6 columns: Priority, Owner, Action, Target, Metric, Status
    table_id = builder._gen_object_id("action_table")
    builder.add_table(
        slide_id, table_id,
        left_inches=0.5,
        top_inches=1.0,
        rows=len(actions) + 1,
        columns=6,
        row_height_inches=0.35,
        col_width_inches=1.5
    )


def _render_comparison_table(builder: GoogleSlidesBatchBuilder, slide_id: str, elements: Dict[str, Any]):
    """Render comparison table on slide."""
    periods = elements.get("periods", [])
    metrics = elements.get("metrics", [])

    # Table with columns: Metric + one per period
    table_id = builder._gen_object_id("comp_table")
    builder.add_table(
        slide_id, table_id,
        left_inches=0.5,
        top_inches=1.0,
        rows=len(metrics) + 1,
        columns=len(periods) + 1,
        row_height_inches=0.3,
        col_width_inches=2.0
    )
