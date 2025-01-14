# Geospatial and population data of Vietnam

This project focuses on refining Vietnam's boundaries (ward and district levels) and combines population data to support map visualization of population/population density across the whole country.

The data supports several use cases in location analyses, such as density of retail stores vs population density, or the estimated customer base shared by each retail store.

## Usage

Vietnam's refined boundaries:
- **VN_Boundaries_District.json**: boundaries of each district, with a distinct `dist_id`, and names of relevant administrative levels (with and without diacritics)
- **VN_Boundaries_Ward.json**: boundaries of each ward, with a distinct `dist_id` and `ward_id`, and names of relevant administrative levels (with and without diacritics)

Vietnam's population:
- *VN_Population_ward.csv*: depicts population as a whole and per urban or rural area, in addition to population density, in each ward
- *VN_HouseholdPop_ward.csv*: depicts the number of household by its size as a whole and per urban or rural area in each ward
- *VN_YoungPop_dist.csv*: depicts population by age (15-34 years of age) as a whole and per urban or rural area, in addition to population density, in each ward

## Example

[WinCommerce Map WebApp](https://github.com/hgscarlette/wcmmap-app)

## Data sources

VN population data is synthesized from [Population and Housing Census 01/4/2019](http://portal.thongke.gov.vn/khodulieudanso2019).
VN boundaries are sourced from [GADM maps and data](https://gadm.org) and the CityScope project run by [City Science Lab @ Ho Chi Minh City](https://www.media.mit.edu/projects/city-science-lab-ho-chi-minh-city/overview/).
