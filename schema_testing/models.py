"""Quick setup: https://www.learndatasci.com/tutorials/using-databases-python-postgres-sqlalchemy-and-alembic/"""

from decimal import Decimal
from re import I
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, Date, ForeignKey, Numeric, TIMESTAMP
from sqlalchemy.orm import relation, relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.selectable import FromClause
from sqlalchemy.sql.sqltypes import Time

Base = declarative_base()

# many_to_many join tables
campaign_user = Table('campaign_user', Base.metadata,
    Column('campaign_id', ForeignKey('campaign.id'), primary_key=True),
    Column('user_id', ForeignKey('user.id'), primary_key=True)
)

dive_user = Table('dive_user', Base.metadata,
    Column('dive_id', ForeignKey('dive.id'), primary_key=True),
    Column('user_id', ForeignKey('user.id'), primary_key=True)
)

# DONE
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    # TODO will come from a controlled vocab.
    role = Column(String, nullable=False)
    email = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    registration_date = Column(TIMESTAMP(timezone=True), nullable=False)
    led_campaigns = relationship("Campaign", back_populates="lead_user", cascade="all, delete", passive_deletes=True)
    campaigns = relationship("Campaign", secondary=campaign_user, back_populates="users")
    dives = relationship("Dive", secondary=dive_user, back_populates="divers")
    def __repr__(self):
        return f"<User(id='{self.id}', role='{self.role}', email={self.email}, user_name={self.user_name})>"


# DONE
class Campaign(Base):
    __tablename__ = "campaign"
    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    lead_user = relationship("User", back_populates="led_campaigns")
    assays = relationship("Assay", back_populates="campaign", cascade="all, delete", passive_deletes=True)
    users = relationship("User", secondary=campaign_user, back_populates="campaigns")
    name = Column(String(100), nullable=False)
    start_date = Column(TIMESTAMP(timezone=True), nullable=False)
    end_date = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Having this as nullable=False will enforce that the lead_user
    # creates an NCBI BioProject object (https://www.ncbi.nlm.nih.gov/bioproject?cmd=Retrieve)
    ncbi_bio_project_accession = Column(String(10), nullable=False)
    


# DONE
class Site(Base):
    __tablename__ = "site"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dives = relationship("Dive", back_populates="site", cascade="all, delete", passive_deletes=True)
    environment_records = relationship("EnvironmentRecord", back_populates="site", cascade="all, delete", passive_deletes=True)
    latitude = Column(Numeric(precision=8, scale=6), nullable=False)
    longitude = Column(Numeric(precision=8, scale=6), nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    abbreviation_code = Column(String(100), unique=True, nullable=False)
    region_id = Column(Integer, ForeignKey("region.id", ondelete="CASCADE"), nullable=False)
    region = relationship("Region", back_populates="sites")
    # TODO constraint: Should be valid timezone ID
    # (https://docs.vmware.com/en/vRealize-Orchestrator/
    # 8.4/com.vmware.vrealize.orchestrator-use-plugins.doc/
    # GUID-83EBD74D-B5EC-4A0A-B54E-8E45BE2928C2.html)
    time_zone = Column(Integer, nullable=False)
    geo_loc_name = Column(String(100), nullable=False)
    env_broad_scale = Column(String(100), nullable=False)
    env_local_scale = Column(String(100), nullable=False)
    env_medium = Column(String(100), nullable=False)
    colonies = relationship("Colony", back_populates="site", cascade="all, delete", passive_deletes=True)

class EnvironmentRecord(Base):
    __tablename__ = "environment_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    site = relationship("Site", back_populates="environment_records")
    assays = relationship("Assay", back_populates="environment_record", cascade="all, delete", passive_deletes=True)
    record_timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    # TODO determine format for turbidity
    turbidity = Column(Numeric(precision=6, scale=3), nullable=True)
    sea_surface_temperature = Column(Numeric(precision=4, scale=2), nullable=True)
    sea_surface_temperature_stdev = Column(Numeric(precision=4, scale=2), nullable=True)
    # TODO determine format for chlorophyl a
    chlorophyll_a = Column(Numeric(precision=4, scale=2), nullable=True)
    # TODO determine format for salinity
    salinity = Column(Numeric(precision=4, scale=2), nullable=True)
    ph = Column(Numeric(precision=4, scale=2), nullable=True)
    dissolved_oxygen = Column(Numeric(precision=5, scale=2), nullable=True)
    mean_monthly_maximum = Column(Numeric(precision=4, scale=2), nullable=True)
    thermall_stress_anomaly_frequency = Column(Numeric(precision=4, scale=2), nullable=True)
    thermal_stress_anomaly_stdev = Column(Numeric(precision=4, scale=2), nullable=True)
    # TODO determine the units and format of coral_cover
    coral_cover = Column(Numeric(precision=4, scale=2), nullable=True)

# DONE
class Region(Base):
    __tablename__ = "region"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    # TODO check to see if this needs to be linked to a controlled vocab from NCBI
    abbreviation = Column(String(3), nullable=False)
    sites = relationship("Site", back_populates="region", cascade="all, delete", passive_deletes=True)

# DONE
class Dive(Base):
    __tablename__ = "dive"
    id = Column(Integer, primary_key=True, autoincrement=True)
    colonies = relationship("Colony", back_populates="dive", cascade="all, delete", passive_deletes=True)
    dive_table_photos = relationship("DiveTablePhoto", back_populates="dive", cascade="all, delete", passive_deletes=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"))
    site = relationship("Site", back_populates="dives")
    divers = relationship("User", secondary=dive_user, back_populates="dives")
    # TODO this may become label and be a combination of other labels
    name = Column(String(100), nullable=False)
    # The in and out times should be provided as local time
    # on the input sheets i.e. not correcting for the the time zone of the dive site.
    # However, these times should be corrected using the time zone associated with site
    # for entry into the database so that the times are in UTC
    time_in = Column(TIMESTAMP(timezone=True), nullable=False)
    time_out = Column(TIMESTAMP(timezone=True), nullable=False)
    # Depth in meters with 2 decimal places.
    max_depth = Column(Numeric(precision=5, scale=2), nullable=False)
    # This will be calculated as time_out - time_in (above)
    # TODO question for Prasantha: is it a good/bad idea to store
    # 'derived' data like this,
    # or is it best to calculate it as part of the query.
    # i.e. have a query where time_out - time_in > XXX
    duration = Column(Integer, nullable=False)
    # Probably best if this is a controlled vocabulary
    # TODO constraint: specifiy the vocab; Have an 'other' category.
    purpose = Column(String(100), nullable=False)
    # Freehand value for additional information
    comments = Column(String(1000), nullable=True)
    # deg C of the water logged by the users dive computer
    temperature = Column(Numeric(precision=2, scale=2))

# DONE
class CoralSpecies(Base):
    __tablename__ = "coral_species"
    id = Column(Integer, primary_key=True, autoincrement=True)
    phylum_tax = Column(String(50))
    class_tax = Column(String(50))
    order_tax = Column(String(50))
    family_tax = Column(String(50))
    genus_tax = Column(String(50))
    species_monomial_tax = Column(String(50))
    species_binomial_tax = Column(String(100))
    # TODO Build in a check to make sure that this is a valid ID
    # in the NCBI taxonomy database (https://www.ncbi.nlm.nih.gov/taxonomy)
    ncbi_tax_id = Column(Integer)
    abbreviation = Column(String(10))
    colonies = relationship("Colony", back_populates="coral_species", cascade="all, delete", passive_deletes=True)

# DONE
class Colony(Base):
    __tablename__ = "colony"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Many to one relationship to coral_species
    coral_species_id = Column(Integer, ForeignKey('coral_species.id', ondelete="CASCADE"), nullable=False)
    coral_species = relationship("CoralSpecies", back_populates="colonies")
    # Many to one relationship to dive
    dive_id = Column(Integer, ForeignKey('dive.id', ondelete="CASCADE"), nullable=False)
    dive = relationship("Dive", back_populates="colonies")
    # Many to one relationship to site
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    site = relationship("Site", back_populates="colonies")
    time_collected = Column(TIMESTAMP(timezone=True), nullable=False)
    # TODO assert: This should be <= to dive.max_depth
    depth_collected = Column(Numeric(precision=5, scale=2), nullable=False)
    colony_photos = relationship("ColonyPhoto", back_populates="colony", cascade="all, delete", passive_deletes=True)
    fragments = relationship("Fragment", back_populates="colony", cascade="all, delete", passive_deletes=True)

# DONE
class ColonyPhoto(Base):
    __tablename__ = "colony_photo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    colony_id = Column(Integer, ForeignKey(column="colony.id", ondelete="CASCADE"), nullable=False)
    colony = relationship("Colony", back_populates="colony_photos")
    name = Column(String(100), nullable=False)
    url = Column(String(100), nullable=True)

# DONE
class DiveTablePhoto(Base):
    __tablename__ = "diver_table_photo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dive_id = Column(Integer, ForeignKey("dive.id", ondelete="CASCADE"), nullable=False)
    dive = relationship("Dive", back_populates="dive_table_phtotos")
    url = Column(String(100), nullable=True)
    name = Column(String(100), nullable=False)


class Fragment(Base):
    __tablename__ = "fragment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    colony_id = Column(Integer, ForeignKey("colony.id", ondelete="CASCADE"), nullable=False)
    colony = relationship("Colony", back_populates="fragments")
    fragment_photo_id = Column(Integer, ForeignKey("fragment.id", ondelete="CASCADE"), nullable=False)
    fragment_photo = relationship("FragmentPhoto", back_populates="fragments")
    sequencing_efforts = relationship("SequencingEffort", back_populates="fragment", cascade="all, delete", passive_deletes=True)
    type = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity':'fragment',
        'polymorphic_on':type
    }


class FragmentPhoto(Base):
    __tablename__ = "fragment_photo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(100), nullable=True)
    name = Column(String(100), nullable=False)
    fragments = relationship("Fragment", back_populates="fragment_photos", cascade="all, delete", passive_deletes=True)


class CBASSNucleicAcidFragment(Fragment):
    __tablename__ = "cbass_nucleic_acid_fragment"
    cbass_nucleic_acid_fragment_id = Column(Integer, primary_key=True, autoincrement=True)
    fragment_id = Column(Integer, ForeignKey("fragment.id", ondelete="CASCADE"), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity':'cbass_nucleic_acid_fragment',
    }


class CBASSAssayFragment(Fragment):
    __tablename__ = "cbass_assay_fragment"
    cbass_assay_fragment_id = Column(Integer, primary_key=True, autoincrement=True)
    fragment_id = Column(Integer, ForeignKey("fragment.id", ondelete="CASCADE"), nullable=False)
    heat_stress_profile_id = Column(Integer, ForeignKey("heat_stress_profile.id", ondelete="CASCADE"), nullable=False)
    heat_stress_profile = relationship("HeatStressProfile", back_populates="cbass_assay_fragments")
    fragment_number = Column(Integer, nullable=False)
    fragment_label = Column(String(100), nullable=False)
    fv_fm_measurement_one = Column(Numeric(precision=5, scale=3), nullable=True)
    fv_fm_measurement_two = Column(Numeric(precision=5, scale=3), nullable=True)
    # Time in minutes
    relative_sampling_time = Column(Integer, nullable=False)
    

    __mapper_args__ = {
        'polymorphic_identity':'cbass_assay_fragment',
    }


class HeatStressProfile(Base):
    __tablename__ = "heat_stress_profile"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cbass_assay_fragments = relationship("CBASSAssayFragment", back_populates="heat_stress_profile", cascade="all, delete", passive_deletes=True)
    cbass_assay_id = Column(Integer, ForeignKey("cbass_assay.cbass_assay_id", ondelete="CASCADE"))
    cbass_assay = relationship("CBASSAssay", back_populates="heat_stress_profiles")
    flow_rate_liters_per_hour = Column(Numeric(precision=6, scale=2), nullable=False)
    # TODO confirm units
    light_level = Column(Numeric(precision=6, scale=3), nullable=True)
    tank_volumne_liter = Column(Integer, nullable=True)
    sea_water_source = Column(String(50), nullable=True)
    relative_challenge_temperature = Column(Numeric(precision=2, scale=1), nullable=False)


class Assay(Base):
    __tablename__ = "assay"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50))
    environment_record_id = Column(Integer, ForeignKey("environment_record.id", ondelete="CASCADE"), nullable=False)
    environment_record = relationship("EnvironmentRecord", back_populates="assays")
    campaign_id = Column(Integer, ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False)
    campaign = relationship("Campaign", back_populates="assays")

    __mapper_args__ = {
        'polymorphic_identity':'assay',
        'polymorphic_on':type
    }


class CBASSAssay(Assay):
    __tablename__ = "cbass_assay"
    cbass_assay_id = Column(Integer, primary_key=True, autoincrement=True)
    assay_id = Column(Integer, ForeignKey("assay.id", ondelete="CASCADE"), nullable=False)
    heat_stress_profiles = relationship("HeatStressProfile", back_populates="cbass_assay", cascade="all, delete", passive_deletes=True)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    stop_time = Column(TIMESTAMP(timezone=True), nullable=False)
    base_line_temp = Column(Numeric(precision=4, scale=2), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity':'cbass_assay',
    }

# This table has no direct practical application currently
# I have put it here to act as a place holder and to show that
# there will be different subclasses of Assay.
class CalcificationAssay(Assay):
    __tablename__ = "calcification_assay"
    calcification_assay_id = Column(Integer, primary_key=True, autoincrement=True)
    assay_id = Column(Integer, ForeignKey("assay.id", ondelete="CASCADE"), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity':'calcification_assay',
    }

class NCBIBioSample(Base):
    __tablename__ = "ncbi_biosample"
    id = Column(Integer, primary_key=True, autoincrement=True)
    accession = Column(String(50), nullable=True)
    sample_name = Column(String(100), nullable=False)
    extraction_label = Column(String(100), nullable=False)
    sequencing_efforts = relationship("SequencingEffort", back_populates="ncbi_biosample", cascade="all, delete", passive_deletes=True)

class SequencingEffort(Base):
    __tablename__ = "sequencing_effort"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fragment_id = Column(Integer, ForeignKey("fragment.id", ondelete="CASCADE"), nullable=False)
    fragment = relationship("Fragment", back_populates="sequencing_efforts")
    sequencing_effort_protocol_id = Column(Integer, ForeignKey("sequencing_effort_protocol.id", ondelete="CASCADE"), nullable=True)
    sequencing_effort_protocol = relationship("SequencingEffortProtocol", back_populates="sequencing_efforts", cascade="all, delete", passive_deletes=True)
    ncbi_biosample_id = Column(Integer, ForeignKey("ncbi_biosample.id", ondelete="CASCADE"), nullable=True)
    ncbi_biosample = relationship("NCBIBioSample", back_populates="sequencing_efforts")
    type = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort',
        'polymorphic_on':type
    }

class SequencingEffortMetagnomic(SequencingEffort):
    __tablename__ = "sequencing_effort_metagenomic"
    sequencing_effort_metagenomic_id = Column(Integer, primary_key=True, autoincrement=True)
    sequencing_effort_id = Column(Integer, ForeignKey("sequencing_effort.id", ondelete="CASCADE"), nullable=True)
    
    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort_metagenomic',
    }

class SequencingEffortRNASeq(SequencingEffort):
    __tablename__ = "sequencing_effort_rna_seq"
    sequencing_effort_rna_seq_id = Column(Integer, primary_key=True, autoincrement=True)
    sequencing_effort_id = Column(Integer, ForeignKey("sequencing_effort.id", ondelete="CASCADE"), nullable=True)
    
    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort_rna_seq',
    }

class SequencingEffortBarcode(SequencingEffort):
    __tablename__ = "sequencing_effort_barcode"
    sequencing_effort_barcode_id = Column(Integer, primary_key=True, autoincrement=True)
    sequencing_effort_id = Column(Integer, ForeignKey("sequencing_effort.id", ondelete="CASCADE"), nullable=True)
    barcode = Column(String(50), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort_barcode',
    }

class SequencingEffortProtocol(Base):
    __tablename__ = "sequencing_effort_protocol"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequencing_efforts = relationship("SequencingEffort", back_populates="sequencing_effort_protocol", cascade="all, delete", passive_deletes=True)
    name = Column(String(100), nullable=False)
    library_type = Column(String(50), nullable=False)
    url = Column(String(100), nullable=True)
