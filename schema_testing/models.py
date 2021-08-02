"""Quick setup: https://www.learndatasci.com/tutorials/using-databases-python-postgres-sqlalchemy-and-alembic/"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, Date, ForeignKey, Numeric, TIMESTAMP
from sqlalchemy.orm import relation, relationship
from sqlalchemy.sql.sqltypes import Time

Base = declarative_base()


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
    
    def __repr__(self):
        return f"<User(id='{self.id}', role='{self.role}', email={self.email}, user_name={self.user_name})>"


class Campaign(Base):
    __tablename__ = "campaign"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    start_date = Column(TIMESTAMP(timezone=True), nullable=False)
    end_date = Column(TIMESTAMP(timezone=True), nullable=False)
    lead_user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    lead_user = relationship("User", back_populates="led_campaigns")

# DONE
class Site(Base):
    __tablename__ = "site"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dives = relationship("Dive", back_populates="site", cascade="all, delete", passive_deletes=True)
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
    time_collected = Column(TIMESTAMP(timezone=True), nullable=False)
    # TODO assert: This should be <= to dive.max_depth
    depth_collected = Column(Numeric(precision=5, scale=2), nullable=False)
    colony_photos = relationship("ColonyPhoto", back_populates="colony", cascade="all, delete", passive_deletes=True)

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

