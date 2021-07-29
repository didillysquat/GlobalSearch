from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, Date, ForeignKey, Numeric
from sqlalchemy.orm import relation, relationship

Base = declarative_base()



class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    role = Column(String)
    email = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    user_name = Column(String)
    registration_date = Column(Date)
    
    def __repr__(self):
        return f"<User(id='{self.id}', role='{self.role}', email={self.email}, user_name={self.user_name})>"

# DONE
class CoralSpecies(Base):
    __tablename__ = "coral_species"
    id = Column(Integer, primary_key=True)
    phylum_tax = Column(String(50))
    class_tax = Column(String(50))
    order_tax = Column(String(50))
    family_tax = Column(String(50))
    genus_tax = Column(String(50))
    species_monomial_tax = Column(String(50))
    species_binomial_tax = Column(String(100))
    ncbi_tax_id = Column(Integer)
    abbreviation = Column(String(10))
    colonies = relationship("Colony")


class Site(Base):
    __tablename__ = "site"
    id = Column(Integer, primary_key=True)
    dives = relationship("Dive")
    latitude = Column(Numeric(precision=8, scale=6), nullable=False)
    longitude = Column(Numeric(precision=8, scale=6), nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    abbreviation_code = Column(String(100), unique=True, nullable=False)
    region_id = Column(Integer, ForeignKey("region.id"), nullable=False)
    time_zone = Column(Integer(3), nullable=False)
    geo_loc_name = Column(String(100), nullable=False)
    env_broad_scale = Column(String(100), nullable=False)
    env_local_scale = Column(String(100), nullable=False)
    env_medium = Column(String(100), nullable=False)

class Region(Base):
    __tablename__ = "region"
    id = Column(Integer, primary_key=True)

class Dive(Base):
    __tablename__ = "dive"
    id = Column(Integer, primary_key=True)
    colonies = relationship("colony")
    site_id = Column(Integer, ForeignKey("site.id"))

class Colony(Base):
    __tablename__ = "colony"
    id = Column(Integer, primary_key=True)
    # Many to one relationship to coral_species
    coral_species_id = Column(Integer, ForeignKey('coral_species.id'))
    # Many to one relationship to dive
    dive_id = Column(Integer, ForeignKey('dive.id'))



