"""Verified Rwanda central and local government institution catalog.

This snapshot intentionally stores institutions, not office holders, because
ministerial appointments change independently from the reporting hierarchy.
The source portal also lists broad directories (health facilities, diplomatic
missions, and sports federations); those are not modeled as single institutions.
"""

from dataclasses import dataclass
from datetime import date


CENTRAL_GOVERNMENT_SOURCE = "https://www.gov.rw/government/institutions/ministries"
LOCAL_GOVERNMENT_SOURCE = "https://www.gov.rw/government/directory/local-government"
CATALOG_VERIFIED_ON = date(2026, 9, 30)


@dataclass(frozen=True)
class RwandaInstitution:
    code: str
    name: str
    institution_type: str
    parent_code: str | None = None
    short_name: str | None = None
    source_url: str = CENTRAL_GOVERNMENT_SOURCE
    description: str | None = None


def _institution(
    code: str,
    name: str,
    institution_type: str,
    parent_code: str | None = None,
    *,
    short_name: str | None = None,
    source_url: str = CENTRAL_GOVERNMENT_SOURCE,
    description: str | None = None,
) -> RwandaInstitution:
    return RwandaInstitution(
        code=code,
        name=name,
        institution_type=institution_type,
        parent_code=parent_code,
        short_name=short_name or code,
        source_url=source_url,
        description=description,
    )


# The ordering is significant: parents precede their children for portable,
# deterministic migration and synchronization behavior.
RWANDA_GOVERNMENT_INSTITUTIONS: tuple[RwandaInstitution, ...] = (
    _institution("MINAGRI", "Ministry of Agriculture and Animal Resources", "ministry"),
    _institution("MOD", "Ministry of Defence", "ministry"),
    _institution("MINEDUC", "Ministry of Education", "ministry"),
    _institution("MOE", "Ministry of Environment", "ministry", short_name="MoE"),
    _institution("MINEMA", "Ministry in Charge of Emergency Management", "ministry"),
    _institution("MINECOFIN", "Ministry of Finance and Economic Planning", "ministry"),
    _institution(
        "MINAFFET",
        "Ministry of Foreign Affairs and International Cooperation",
        "ministry",
    ),
    _institution("MIGEPROF", "Ministry of Gender and Family Promotion", "ministry"),
    _institution("MOH", "Ministry of Health", "ministry", short_name="MoH"),
    _institution("MINICT", "Ministry of ICT and Innovation", "ministry"),
    _institution("MININFRA", "Ministry of Infrastructure", "ministry"),
    _institution("MININTER", "Ministry of Interior", "ministry"),
    _institution("MINIJUST", "Ministry of Justice", "ministry"),
    _institution("MINALOC", "Ministry of Local Government", "ministry"),
    _institution("MIFOTRA", "Ministry of Public Service and Labour", "ministry"),
    _institution("MINISPORTS", "Ministry of Sports", "ministry"),
    _institution("MINICOM", "Ministry of Trade and Industry", "ministry"),
    _institution("MINIYOUTH", "Ministry of Youth and Arts", "ministry"),
    _institution("MINUBUMWE", "Ministry of National Unity and Civic Engagement", "ministry"),
    _institution("RAB", "Rwanda Agricultural Board", "agency", "MINAGRI"),
    _institution("NAEB", "National Agriculture Export Development Board", "agency", "MINAGRI"),
    _institution("RPA", "Rwanda Peace Academy", "public_institution", "MOD"),
    _institution("ZIGAMA-CSS", "Zigama Credit and Saving Sacco", "public_institution", "MOD", short_name="ZIGAMA CSS"),
    _institution("RMH", "Rwanda Military Hospital", "public_institution", "MOD"),
    _institution("REB", "Rwanda Basic Education Board", "agency", "MINEDUC"),
    _institution("HEC", "Higher Education Council", "commission", "MINEDUC"),
    _institution("NESA", "National Examination and School Inspection Authority", "authority", "MINEDUC"),
    _institution("RTB", "Rwanda TVET Board", "agency", "MINEDUC"),
    _institution("UR", "University of Rwanda", "public_institution", "MINEDUC"),
    _institution("RP", "Rwanda Polytechnic", "public_institution", "MINEDUC"),
    _institution("CNRU", "Rwanda National Commission for UNESCO", "commission", "MINEDUC"),
    _institution("REMA", "Rwanda Environment Management Authority", "authority", "MOE"),
    _institution("RLMUA", "Rwanda Land Management and Use Authority", "authority", "MOE"),
    _institution("RWB", "Rwanda Water Resources Board", "agency", "MOE"),
    _institution("RMA", "Rwanda Meteorology Agency", "agency", "MOE"),
    _institution("FONERWA", "Rwanda Green Fund", "public_institution", "MOE"),
    _institution("RSSB", "Rwanda Social Security Board", "agency", "MINECOFIN"),
    _institution("OAG", "Office of the Auditor General", "other_government_entity", "MINECOFIN"),
    _institution("RRA", "Rwanda Revenue Authority", "authority", "MINECOFIN"),
    _institution("NISR", "National Institute of Statistics of Rwanda", "public_institution", "MINECOFIN"),
    _institution("SGF", "Special Guarantee Fund", "public_institution", "MINECOFIN"),
    _institution("AGDF", "Agaciro Development Fund", "public_institution", "MINECOFIN", short_name="AgDF"),
    _institution("FIC", "Financial Intelligence Centre", "public_institution", "MINECOFIN"),
    _institution("CMA", "Capital Market Authority", "authority", "MINECOFIN"),
    _institution("RNIT", "Rwanda National Investment Trust", "public_institution", "MINECOFIN"),
    _institution(
        "RFL-FINANCE",
        "Rwanda Finance Limited",
        "public_institution",
        "MINECOFIN",
        short_name="RFL",
        description="Machine code disambiguates this institution from Rwanda Forensic Laboratory.",
    ),
    _institution("RPPA", "Rwanda Public Procurement Authority", "authority", "MINECOFIN"),
    _institution("RCI", "Rwanda Cooperation Initiative", "agency", "MINAFFET"),
    _institution("NWC", "National Women's Council", "commission", "MIGEPROF"),
    _institution("NCDA", "National Child Development Agency", "agency", "MIGEPROF"),
    _institution("RBC", "Rwanda Biomedical Centre", "agency", "MOH"),
    _institution("CHUK", "University Teaching Hospital of Kigali", "public_institution", "MOH"),
    _institution("CHUB", "University Teaching Hospital of Butare", "public_institution", "MOH"),
    _institution("RFDA", "Rwanda Food and Drugs Authority", "authority", "MOH", short_name="FDA"),
    _institution("RISA", "Rwanda Information Society Authority", "authority", "MINICT"),
    _institution("RURA", "Rwanda Utilities Regulatory Authority", "authority", "MINICT"),
    _institution("RDB", "Rwanda Development Board", "agency", "MINICT"),
    _institution("NPO", "National Post Office", "public_institution", "MINICT"),
    _institution("RCAA", "Rwanda Civil Aviation Authority", "authority", "MININFRA"),
    _institution("RTDA", "Rwanda Transport Development Agency", "agency", "MININFRA"),
    _institution("RHA", "Rwanda Housing Authority", "authority", "MININFRA"),
    _institution("REG", "Rwanda Energy Group", "public_institution", "MININFRA"),
    _institution("WASAC", "Water and Sanitation Corporation", "public_institution", "MININFRA"),
    _institution("RMF", "Rwanda Maintenance Fund", "public_institution", "MININFRA"),
    _institution("RNP", "Rwanda National Police", "public_institution", "MININTER"),
    _institution(
        "RCS",
        "Rwanda Correctional Service",
        "public_institution",
        "MININTER",
        description=(
            "The Government portal also lists RCS with Justice. Interior is the single "
            "primary reporting parent here to prevent duplicate asset totals."
        ),
    ),
    _institution("RLRC", "Rwanda Law Reform Commission", "commission", "MINIJUST"),
    _institution("NPPA", "National Public Prosecution Authority", "authority", "MINIJUST"),
    _institution("RIB", "Rwanda Investigation Bureau", "agency", "MINIJUST"),
    _institution("ILPD", "Institute of Legal Practice and Development", "public_institution", "MINIJUST"),
    _institution(
        "RFL-FORENSIC",
        "Rwanda Forensic Laboratory",
        "public_institution",
        "MINIJUST",
        short_name="RFL",
        description="Machine code disambiguates this institution from Rwanda Finance Limited.",
    ),
    _institution("NEC", "National Electoral Commission", "commission", "MINALOC"),
    _institution("NIDA", "National Identification Agency", "agency", "MINALOC"),
    _institution("NRS", "National Rehabilitation Service", "agency", "MINALOC"),
    _institution("RDRC", "Rwanda Demobilisation and Reintegration Commission", "commission", "MINALOC"),
    _institution("LODA", "Local Administrative Entities Development Agency", "agency", "MINALOC"),
    _institution("NCPD", "National Council of Persons with Disabilities", "commission", "MINALOC"),
    _institution("RBA", "Rwanda Broadcasting Agency", "agency", "MINALOC"),
    _institution("RSB", "Rwanda Standards Board", "agency", "MINICOM"),
    _institution("NIRDA", "National Industrial Research and Development Agency", "agency", "MINICOM"),
    _institution("RCA", "Rwanda Cooperatives Agency", "agency", "MINICOM"),
    _institution("RICA", "Rwanda Inspectorate, Competition and Consumer Protection Authority", "authority", "MINICOM"),
    _institution("NYC", "National Youth Council", "commission", "MINIYOUTH"),
    _institution("RCHA", "Rwanda Cultural Heritage Academy", "authority", "MINIYOUTH"),
    _institution("CHENO", "Chancellery for Heroes, National Orders and Decorations of Honour", "commission", "MINIYOUTH"),
    _institution("COK", "City of Kigali", "city", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("PROV-EAST", "Eastern Province", "province", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("PROV-NORTH", "Northern Province", "province", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("PROV-SOUTH", "Southern Province", "province", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("PROV-WEST", "Western Province", "province", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-GASABO", "Gasabo District", "district", "COK", short_name="Gasabo", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-KICUKIRO", "Kicukiro District", "district", "COK", short_name="Kicukiro", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NYARUGENGE", "Nyarugenge District", "district", "COK", short_name="Nyarugenge", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-BUGESERA", "Bugesera District", "district", "PROV-EAST", short_name="Bugesera", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-GATSIBO", "Gatsibo District", "district", "PROV-EAST", short_name="Gatsibo", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-KAYONZA", "Kayonza District", "district", "PROV-EAST", short_name="Kayonza", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-KIREHE", "Kirehe District", "district", "PROV-EAST", short_name="Kirehe", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NGOMA", "Ngoma District", "district", "PROV-EAST", short_name="Ngoma", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NYAGATARE", "Nyagatare District", "district", "PROV-EAST", short_name="Nyagatare", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-RWAMAGANA", "Rwamagana District", "district", "PROV-EAST", short_name="Rwamagana", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-BURERA", "Burera District", "district", "PROV-NORTH", short_name="Burera", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-GAKENKE", "Gakenke District", "district", "PROV-NORTH", short_name="Gakenke", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-GICUMBI", "Gicumbi District", "district", "PROV-NORTH", short_name="Gicumbi", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-MUSANZE", "Musanze District", "district", "PROV-NORTH", short_name="Musanze", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-RULINDO", "Rulindo District", "district", "PROV-NORTH", short_name="Rulindo", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-GISAGARA", "Gisagara District", "district", "PROV-SOUTH", short_name="Gisagara", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-HUYE", "Huye District", "district", "PROV-SOUTH", short_name="Huye", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-KAMONYI", "Kamonyi District", "district", "PROV-SOUTH", short_name="Kamonyi", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-MUHANGA", "Muhanga District", "district", "PROV-SOUTH", short_name="Muhanga", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NYAMAGABE", "Nyamagabe District", "district", "PROV-SOUTH", short_name="Nyamagabe", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NYANZA", "Nyanza District", "district", "PROV-SOUTH", short_name="Nyanza", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NYARUGURU", "Nyaruguru District", "district", "PROV-SOUTH", short_name="Nyaruguru", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-RUHANGO", "Ruhango District", "district", "PROV-SOUTH", short_name="Ruhango", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-KARONGI", "Karongi District", "district", "PROV-WEST", short_name="Karongi", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NGORORERO", "Ngororero District", "district", "PROV-WEST", short_name="Ngororero", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NYABIHU", "Nyabihu District", "district", "PROV-WEST", short_name="Nyabihu", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-NYAMASHEKE", "Nyamasheke District", "district", "PROV-WEST", short_name="Nyamasheke", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-RUBAVU", "Rubavu District", "district", "PROV-WEST", short_name="Rubavu", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-RUSIZI", "Rusizi District", "district", "PROV-WEST", short_name="Rusizi", source_url=LOCAL_GOVERNMENT_SOURCE),
    _institution("DIST-RUTSIRO", "Rutsiro District", "district", "PROV-WEST", short_name="Rutsiro", source_url=LOCAL_GOVERNMENT_SOURCE),
)


assert len({item.code for item in RWANDA_GOVERNMENT_INSTITUTIONS}) == len(
    RWANDA_GOVERNMENT_INSTITUTIONS
)
