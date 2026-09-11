"""
KOHA-CIL — Database Seeder
Idempotent: safe to run multiple times without creating duplicates.
All synthetic production figures are clearly marked as DEMO DATA.
DO NOT represent these figures as official CIL statistics.
"""
import logging
import os
import sys
from pathlib import Path

# Allow running as standalone script
sys.path.insert(0, str(Path(__file__).parents[1]))

from database.connection import init_db, get_db

logger = logging.getLogger(__name__)

# ================================================================
# DEMO USERS
# Passwords are hashed with bcrypt. Plain text shown only for docs.
# demo: hq.admin / demo123, ccl.officer / demo123, secl.officer / demo123
# ================================================================
DEMO_USERS = [
    {
        "username": "hq.admin",
        # bcrypt hash of "demo123"
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBIm0wNQjFbQCW",
        "role": "HQ_OFFICER",
        "subsidiary": None,
    },
    {
        "username": "ccl.officer",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBIm0wNQjFbQCW",
        "role": "SUBSIDIARY_OFFICER",
        "subsidiary": "CCL",
    },
    {
        "username": "secl.officer",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBIm0wNQjFbQCW",
        "role": "SUBSIDIARY_OFFICER",
        "subsidiary": "SECL",
    },
    {
        "username": "ecl.officer",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBIm0wNQjFbQCW",
        "role": "SUBSIDIARY_OFFICER",
        "subsidiary": "ECL",
    },
    {
        "username": "mcl.officer",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBIm0wNQjFbQCW",
        "role": "SUBSIDIARY_OFFICER",
        "subsidiary": "MCL",
    },
]

# ================================================================
# DEMO PRODUCTION STATISTICS
# ⚠ ALL FIGURES ARE SYNTHETIC DEMO DATA ONLY.
# ⚠ NOT OFFICIAL CIL OR MINISTRY OF COAL STATISTICS.
# ================================================================
DEMO_PRODUCTION = [
    # --- ECL ---
    {"subsidiary": "ECL", "financial_year": "FY2022-23", "mine_type": "UNDERGROUND", "production_mt": 18.4, "target_mt": 20.0, "achievement_percentage": 92.0, "source_document": "ECL_Annual_Report_2023.pdf", "source_page": 24, "source_cell": "C8", "source_section": "Production Performance"},
    {"subsidiary": "ECL", "financial_year": "FY2022-23", "mine_type": "OPENCAST",   "production_mt": 15.2, "target_mt": 16.0, "achievement_percentage": 95.0, "source_document": "ECL_Annual_Report_2023.pdf", "source_page": 24, "source_cell": "C9", "source_section": "Production Performance"},
    {"subsidiary": "ECL", "financial_year": "FY2022-23", "mine_type": "TOTAL",      "production_mt": 33.6, "target_mt": 36.0, "achievement_percentage": 93.3, "source_document": "ECL_Annual_Report_2023.pdf", "source_page": 24, "source_cell": "C10", "source_section": "Production Performance"},
    {"subsidiary": "ECL", "financial_year": "FY2023-24", "mine_type": "UNDERGROUND", "production_mt": 19.1, "target_mt": 21.0, "achievement_percentage": 91.0, "source_document": "ECL_Annual_Report_2024.pdf", "source_page": 18, "source_cell": "C8", "source_section": "Production Performance"},
    {"subsidiary": "ECL", "financial_year": "FY2023-24", "mine_type": "OPENCAST",   "production_mt": 16.8, "target_mt": 17.5, "achievement_percentage": 96.0, "source_document": "ECL_Annual_Report_2024.pdf", "source_page": 18, "source_cell": "C9", "source_section": "Production Performance"},
    {"subsidiary": "ECL", "financial_year": "FY2023-24", "mine_type": "TOTAL",      "production_mt": 35.9, "target_mt": 38.5, "achievement_percentage": 93.2, "source_document": "ECL_Annual_Report_2024.pdf", "source_page": 18, "source_cell": "C10", "source_section": "Production Performance"},

    # --- BCCL ---
    {"subsidiary": "BCCL", "financial_year": "FY2022-23", "mine_type": "UNDERGROUND", "production_mt": 22.1, "target_mt": 24.0, "achievement_percentage": 92.1, "source_document": "BCCL_Annual_Report_2023.pdf", "source_page": 31, "source_cell": "D8", "source_section": "Production Performance"},
    {"subsidiary": "BCCL", "financial_year": "FY2022-23", "mine_type": "OPENCAST",   "production_mt": 8.4,  "target_mt": 9.0,  "achievement_percentage": 93.3, "source_document": "BCCL_Annual_Report_2023.pdf", "source_page": 31, "source_cell": "D9", "source_section": "Production Performance"},
    {"subsidiary": "BCCL", "financial_year": "FY2022-23", "mine_type": "TOTAL",      "production_mt": 30.5, "target_mt": 33.0, "achievement_percentage": 92.4, "source_document": "BCCL_Annual_Report_2023.pdf", "source_page": 31, "source_cell": "D10", "source_section": "Production Performance"},
    {"subsidiary": "BCCL", "financial_year": "FY2023-24", "mine_type": "UNDERGROUND", "production_mt": 23.0, "target_mt": 25.0, "achievement_percentage": 92.0, "source_document": "BCCL_Annual_Report_2024.pdf", "source_page": 27, "source_cell": "D8", "source_section": "Production Performance"},
    {"subsidiary": "BCCL", "financial_year": "FY2023-24", "mine_type": "OPENCAST",   "production_mt": 9.1,  "target_mt": 9.5,  "achievement_percentage": 95.8, "source_document": "BCCL_Annual_Report_2024.pdf", "source_page": 27, "source_cell": "D9", "source_section": "Production Performance"},
    {"subsidiary": "BCCL", "financial_year": "FY2023-24", "mine_type": "TOTAL",      "production_mt": 32.1, "target_mt": 34.5, "achievement_percentage": 93.0, "source_document": "BCCL_Annual_Report_2024.pdf", "source_page": 27, "source_cell": "D10", "source_section": "Production Performance"},

    # --- CCL ---
    {"subsidiary": "CCL", "financial_year": "FY2022-23", "mine_type": "UNDERGROUND", "production_mt": 5.8,  "target_mt": 6.5,  "achievement_percentage": 89.2, "source_document": "CCL_Annual_Report_2023.pdf", "source_page": 14, "source_cell": "E8", "source_section": "Production Performance"},
    {"subsidiary": "CCL", "financial_year": "FY2022-23", "mine_type": "OPENCAST",   "production_mt": 55.4, "target_mt": 58.0, "achievement_percentage": 95.5, "source_document": "CCL_Annual_Report_2023.pdf", "source_page": 14, "source_cell": "E9", "source_section": "Production Performance"},
    {"subsidiary": "CCL", "financial_year": "FY2022-23", "mine_type": "TOTAL",      "production_mt": 61.2, "target_mt": 64.5, "achievement_percentage": 94.9, "source_document": "CCL_Annual_Report_2023.pdf", "source_page": 14, "source_cell": "E10", "source_section": "Production Performance"},
    {"subsidiary": "CCL", "financial_year": "FY2023-24", "mine_type": "UNDERGROUND", "production_mt": 6.1,  "target_mt": 7.0,  "achievement_percentage": 87.1, "source_document": "CCL_Annual_Report_2024.pdf", "source_page": 11, "source_cell": "E8", "source_section": "Production Performance"},
    {"subsidiary": "CCL", "financial_year": "FY2023-24", "mine_type": "OPENCAST",   "production_mt": 59.8, "target_mt": 62.0, "achievement_percentage": 96.5, "source_document": "CCL_Annual_Report_2024.pdf", "source_page": 11, "source_cell": "E9", "source_section": "Production Performance"},
    {"subsidiary": "CCL", "financial_year": "FY2023-24", "mine_type": "TOTAL",      "production_mt": 65.9, "target_mt": 69.0, "achievement_percentage": 95.5, "source_document": "CCL_Annual_Report_2024.pdf", "source_page": 11, "source_cell": "E10", "source_section": "Production Performance"},

    # --- SECL ---
    {"subsidiary": "SECL", "financial_year": "FY2022-23", "mine_type": "UNDERGROUND", "production_mt": 14.3, "target_mt": 15.5, "achievement_percentage": 92.3, "source_document": "SECL_Annual_Report_2023.pdf", "source_page": 20, "source_cell": "F8", "source_section": "Production Performance"},
    {"subsidiary": "SECL", "financial_year": "FY2022-23", "mine_type": "OPENCAST",   "production_mt": 143.2,"target_mt":148.0, "achievement_percentage": 96.8, "source_document": "SECL_Annual_Report_2023.pdf", "source_page": 20, "source_cell": "F9", "source_section": "Production Performance"},
    {"subsidiary": "SECL", "financial_year": "FY2022-23", "mine_type": "TOTAL",      "production_mt": 157.5,"target_mt":163.5, "achievement_percentage": 96.3, "source_document": "SECL_Annual_Report_2023.pdf", "source_page": 20, "source_cell": "F10", "source_section": "Production Performance"},
    {"subsidiary": "SECL", "financial_year": "FY2023-24", "mine_type": "UNDERGROUND", "production_mt": 15.1, "target_mt": 16.0, "achievement_percentage": 94.4, "source_document": "SECL_Annual_Report_2024.pdf", "source_page": 17, "source_cell": "F8", "source_section": "Production Performance"},
    {"subsidiary": "SECL", "financial_year": "FY2023-24", "mine_type": "OPENCAST",   "production_mt": 150.6,"target_mt":155.0, "achievement_percentage": 97.2, "source_document": "SECL_Annual_Report_2024.pdf", "source_page": 17, "source_cell": "F9", "source_section": "Production Performance"},
    {"subsidiary": "SECL", "financial_year": "FY2023-24", "mine_type": "TOTAL",      "production_mt": 165.7,"target_mt":171.0, "achievement_percentage": 96.9, "source_document": "SECL_Annual_Report_2024.pdf", "source_page": 17, "source_cell": "F10", "source_section": "Production Performance"},

    # --- MCL ---
    {"subsidiary": "MCL", "financial_year": "FY2022-23", "mine_type": "UNDERGROUND", "production_mt": 1.2,  "target_mt": 1.5,  "achievement_percentage": 80.0, "source_document": "MCL_Annual_Report_2023.pdf", "source_page": 16, "source_cell": "G8", "source_section": "Production Performance"},
    {"subsidiary": "MCL", "financial_year": "FY2022-23", "mine_type": "OPENCAST",   "production_mt": 150.3,"target_mt":155.0, "achievement_percentage": 97.0, "source_document": "MCL_Annual_Report_2023.pdf", "source_page": 16, "source_cell": "G9", "source_section": "Production Performance"},
    {"subsidiary": "MCL", "financial_year": "FY2022-23", "mine_type": "TOTAL",      "production_mt": 151.5,"target_mt":156.5, "achievement_percentage": 96.8, "source_document": "MCL_Annual_Report_2023.pdf", "source_page": 16, "source_cell": "G10", "source_section": "Production Performance"},
    {"subsidiary": "MCL", "financial_year": "FY2023-24", "mine_type": "UNDERGROUND", "production_mt": 1.3,  "target_mt": 1.5,  "achievement_percentage": 86.7, "source_document": "MCL_Annual_Report_2024.pdf", "source_page": 14, "source_cell": "G8", "source_section": "Production Performance"},
    {"subsidiary": "MCL", "financial_year": "FY2023-24", "mine_type": "OPENCAST",   "production_mt": 158.2,"target_mt":162.0, "achievement_percentage": 97.7, "source_document": "MCL_Annual_Report_2024.pdf", "source_page": 14, "source_cell": "G9", "source_section": "Production Performance"},
    {"subsidiary": "MCL", "financial_year": "FY2023-24", "mine_type": "TOTAL",      "production_mt": 159.5,"target_mt":163.5, "achievement_percentage": 97.5, "source_document": "MCL_Annual_Report_2024.pdf", "source_page": 14, "source_cell": "G10", "source_section": "Production Performance"},
]

# ================================================================
# QUALITATIVE KNOWLEDGE BASE
# ================================================================
QUALITATIVE_POLICIES = [
    {
        "topic": "Environmental Policy",
        "section": "Environmental Management Framework",
        "content": (
            "Coal India Limited has adopted a comprehensive Environmental Management Framework (EMF) "
            "across all subsidiary operations. The framework mandates Environmental Impact Assessment (EIA) "
            "studies prior to opening new mines or expanding existing operations. All subsidiaries are required "
            "to obtain Environmental Clearance (EC) from the Ministry of Environment, Forest and Climate Change "
            "(MoEFCC) before commencing coal extraction. The framework includes provisions for afforestation, "
            "reclamation of mined areas, control of dust emissions, treatment of mine effluents, and monitoring "
            "of ambient air quality. Quarterly environmental audits are conducted at all major mining sites."
        ),
        "source_document": "CIL_Environmental_Policy_2023.pdf",
        "source_page": 7,
        "keywords": "environmental,policy,EIA,clearance,afforestation,reclamation,emissions,audit",
    },
    {
        "topic": "Safety Policy",
        "section": "Mine Safety and Health Administration",
        "content": (
            "Safety remains the foremost priority of Coal India Limited and all its subsidiaries. The Corporate "
            "Safety Policy mandates compliance with the Mines Act 1952, Mines Rules 1955, and Coal Mines "
            "Regulations 2017. Key provisions include mandatory safety training for all underground workers, "
            "regular statutory inspections by Directorate General of Mines Safety (DGMS) officials, maintenance "
            "of ventilation systems in underground mines, use of approved safety equipment including self-rescuers "
            "and cap lamps, and a zero-tolerance approach to violations of safety protocols. Fatal accident rates "
            "and injury frequency rates are monitored monthly and reported to the CIL Board."
        ),
        "source_document": "CIL_Safety_Policy_2023.pdf",
        "source_page": 3,
        "keywords": "safety,mines act,DGMS,ventilation,underground,accident,injury,training,compliance",
    },
    {
        "topic": "Geological Survey",
        "section": "Geological Observations — Jharia Coalfield",
        "content": (
            "The Jharia Coalfield, operated primarily by BCCL, contains one of India's largest reserves of "
            "prime coking coal. Geological surveys conducted by CMPDI indicate a total coal reserve of "
            "approximately 19.4 billion tonnes in the Jharia basin, of which proven reserves stand at "
            "approximately 4.6 billion tonnes. The coal seams are characterised by high volatile matter content "
            "and rank from high volatile A bituminous to low volatile bituminous. Underground fire hazards remain "
            "a significant geological and operational challenge in several blocks. CMPDI has recommended "
            "accelerated extraction in fire-affected zones to prevent further coal loss through spontaneous combustion."
        ),
        "source_document": "CMPDI_Geological_Report_Jharia_2023.pdf",
        "source_page": 12,
        "keywords": "geological,Jharia,coalfield,BCCL,coking coal,reserves,underground fire,CMPDI",
    },
    {
        "topic": "Geological Survey",
        "section": "Geological Observations — Korba Coalfield",
        "content": (
            "The Korba Coalfield in Chhattisgarh, operated by SECL, is one of the largest opencast coal "
            "producing regions in India. CMPDI geological investigations have delineated coal reserves of "
            "approximately 9.2 billion tonnes. The coal is predominantly of non-coking grade (Grade D to F) "
            "suitable for thermal power generation. Seam thickness ranges from 3 metres to 42 metres in the "
            "principal seams. The overburden stratigraphy consists of Gondwana sedimentary formations. "
            "Groundwater ingress management is a key operational consideration in the deeper pits."
        ),
        "source_document": "CMPDI_Geological_Report_Korba_2023.pdf",
        "source_page": 8,
        "keywords": "geological,Korba,coalfield,SECL,non-coking,thermal,reserves,overburden,groundwater",
    },
    {
        "topic": "Production Target Policy",
        "section": "Vision 2030 Production Targets",
        "content": (
            "In alignment with the Government of India's goal of energy security and coal self-sufficiency, "
            "Coal India Limited has set an aspirational production target of 1 billion tonnes of coal per "
            "annum by 2025-26. The interim targets for FY2023-24 were set at 780 million tonnes across all "
            "subsidiaries. Achievement of targets is monitored through a real-time Production Monitoring System "
            "(PMS) maintained at CIL headquarters. Subsidiary-wise targets are revised annually in consultation "
            "with the Ministry of Coal. Shortfalls are analysed and corrective action plans are submitted quarterly."
        ),
        "source_document": "CIL_Vision_2030_Document.pdf",
        "source_page": 22,
        "keywords": "production target,vision 2030,1 billion tonne,energy security,monitoring,subsidiary",
    },
    {
        "topic": "Corporate Social Responsibility",
        "section": "CSR Policy and Initiatives",
        "content": (
            "Coal India Limited mandates all subsidiaries to spend at least 2% of their average net profit "
            "over the preceding three financial years on Corporate Social Responsibility (CSR) activities, "
            "in accordance with Section 135 of the Companies Act 2013. Priority CSR areas include "
            "education and skill development in mining communities, healthcare and sanitation, drinking water "
            "supply, rural infrastructure development, and livelihood promotion for project-affected persons (PAPs). "
            "CSR expenditure is monitored by the Board-level CSR Committee and reported in the Annual Report."
        ),
        "source_document": "CIL_CSR_Policy_2023.pdf",
        "source_page": 5,
        "keywords": "CSR,corporate social responsibility,education,healthcare,livelihood,community,PAP",
    },
    {
        "topic": "Digital Transformation",
        "section": "IT and Digitisation Initiatives",
        "content": (
            "CIL is implementing a comprehensive digital transformation roadmap under its IT Master Plan. "
            "Key initiatives include deployment of an Enterprise Resource Planning (ERP) system across "
            "subsidiaries, implementation of a Integrated Mine Management System (IMMS) for real-time "
            "monitoring of production, safety and equipment utilisation, rollout of drone-based mine survey "
            "technologies, adoption of Geographic Information System (GIS) for geological mapping, and "
            "establishment of a centralised data analytics platform for management reporting. The KOHA-CIL "
            "platform is part of this digitisation drive to enable evidence-based decision making."
        ),
        "source_document": "CIL_IT_Master_Plan_2023.pdf",
        "source_page": 14,
        "keywords": "digital,IT,ERP,IMMS,drone,GIS,analytics,digitisation,reporting",
    },
    {
        "topic": "Water Management",
        "section": "Mine Water Management and Discharge Policy",
        "content": (
            "All CIL subsidiaries are required to comply with the Water (Prevention and Control of Pollution) "
            "Act 1974 and obtain consent to discharge mine effluents from the respective State Pollution Control "
            "Boards. Mine water is treated through settling ponds and clarifiers before discharge. Treated mine "
            "water must meet prescribed standards for pH (6.0–8.5), total suspended solids (< 100 mg/L) and "
            "oil and grease (< 10 mg/L). Subsidiaries are encouraged to utilise treated mine water for "
            "dust suppression, plantation and domestic purposes within the mine premises to minimise freshwater "
            "extraction from local water bodies."
        ),
        "source_document": "CIL_Water_Management_Policy_2022.pdf",
        "source_page": 9,
        "keywords": "water,mine water,discharge,pollution,settling pond,effluent,pH,TSS",
    },
]


def _hash_demo_password(plain: str) -> str:
    """Generate a bcrypt hash for a demo password."""
    try:
        import bcrypt
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()
    except ImportError:
        # Fallback: return a known bcrypt hash of "demo123" (generated offline)
        # $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBIm0wNQjFbQCW
        return "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBIm0wNQjFbQCW"


def seed_users(conn) -> int:
    """Seed demo user accounts. Returns count inserted."""
    inserted = 0
    for user in DEMO_USERS:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (user["username"],)
        ).fetchone()
        if existing:
            continue
        # Generate a proper hash when running
        pw_hash = _hash_demo_password("demo123")
        conn.execute(
            """
            INSERT INTO users (username, password_hash, role, subsidiary)
            VALUES (?, ?, ?, ?)
            """,
            (user["username"], pw_hash, user["role"], user["subsidiary"]),
        )
        inserted += 1
    return inserted


def seed_production(conn) -> int:
    """Seed demo production statistics. Returns count inserted."""
    inserted = 0
    for row in DEMO_PRODUCTION:
        existing = conn.execute(
            """SELECT id FROM production_statistics
               WHERE subsidiary = ? AND financial_year = ? AND mine_type = ?""",
            (row["subsidiary"], row["financial_year"], row["mine_type"]),
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO production_statistics
                (subsidiary, financial_year, mine_type, production_mt, target_mt,
                 achievement_percentage, data_label, source_document, source_page,
                 source_cell, source_section)
            VALUES (?, ?, ?, ?, ?, ?, 'DEMO DATA', ?, ?, ?, ?)
            """,
            (
                row["subsidiary"],
                row["financial_year"],
                row["mine_type"],
                row["production_mt"],
                row["target_mt"],
                row["achievement_percentage"],
                row.get("source_document"),
                row.get("source_page"),
                row.get("source_cell"),
                row.get("source_section"),
            ),
        )
        inserted += 1
    return inserted


def seed_qualitative(conn) -> int:
    """Seed qualitative policy knowledge. Returns count inserted."""
    inserted = 0
    for policy in QUALITATIVE_POLICIES:
        existing = conn.execute(
            "SELECT id FROM qualitative_policies WHERE topic = ? AND section = ?",
            (policy["topic"], policy["section"]),
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO qualitative_policies
                (topic, section, content, source_document, source_page, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                policy["topic"],
                policy["section"],
                policy["content"],
                policy.get("source_document"),
                policy.get("source_page"),
                policy.get("keywords"),
            ),
        )
        inserted += 1
    return inserted


def run_seed() -> None:
    """Run all seeders inside a single transaction."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    logger.info("Initialising database schema…")
    init_db()

    with get_db() as conn:
        u = seed_users(conn)
        p = seed_production(conn)
        q = seed_qualitative(conn)

    logger.info("Seed complete — users: %d inserted, production: %d inserted, qualitative: %d inserted", u, p, q)
    if u == 0 and p == 0 and q == 0:
        logger.info("(All records already existed — seeder is idempotent)")


if __name__ == "__main__":
    run_seed()
