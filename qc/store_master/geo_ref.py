# -*- coding: utf-8 -*-
"""India geography reference for MT store-master QC.
Curated from geographic knowledge. No fabricated web sources.
Keys are UPPER-cased, stripped for lookup robustness.
"""

# ---------------------------------------------------------------------------
# 1. CANONICAL CITY SPELLING  (variant UPPER -> canonical Title form)
#    Covers official renames + common misspellings/abbreviations.
# ---------------------------------------------------------------------------
CANONICAL_CITY = {
    # Karnataka
    "BANGALORE": "Bengaluru", "BANGALURU": "Bengaluru", "BENGALORE": "Bengaluru",
    "BANGLORE": "Bengaluru", "BENGALURU": "Bengaluru", "BLR": "Bengaluru",
    "MANGALORE": "Mangaluru", "MANGALURU": "Mangaluru",
    "MYSORE": "Mysuru", "MYSURU": "Mysuru",
    "BELGAUM": "Belagavi", "BELAGAVI": "Belagavi",
    "HUBLI": "Hubballi", "HUBBALLI": "Hubballi", "HUBLI-DHARWAD": "Hubballi",
    "GULBARGA": "Kalaburagi", "KALABURAGI": "Kalaburagi",
    "TUMKUR": "Tumakuru", "TUMAKURU": "Tumakuru",
    "BELLARY": "Ballari", "BALLARI": "Ballari",
    "BIJAPUR": "Vijayapura", "VIJAYAPURA": "Vijayapura",
    "SHIMOGA": "Shivamogga", "SHIVAMOGGA": "Shivamogga",
    "HOSPET": "Hosapete", "HOSAPETE": "Hosapete",
    "CHIKMAGALUR": "Chikkamagaluru", "CHIKKAMAGALURU": "Chikkamagaluru",
    "DAVANGERE": "Davanagere", "DAVANAGERE": "Davanagere",
    # Maharashtra
    "BOMBAY": "Mumbai", "MUMBAI": "Mumbai",
    "POONA": "Pune", "PUNE": "Pune",
    "AURANGABAD": "Chhatrapati Sambhajinagar",  # official 2023 rename
    "OSMANABAD": "Dharashiv",
    # West Bengal
    "CALCUTTA": "Kolkata", "KOLKATA": "Kolkata", "KOLKATTA": "Kolkata",
    "COOCHBEHAR": "Cooch Behar", "COOCH BEHAR": "Cooch Behar",
    # Gujarat
    "BARODA": "Vadodara", "VADODARA": "Vadodara",
    "AHMEDABAD": "Ahmedabad", "AHMADABAD": "Ahmedabad",
    # Kerala
    "TRIVANDRUM": "Thiruvananthapuram", "THIRUVANANTHAPURAM": "Thiruvananthapuram",
    "COCHIN": "Kochi", "KOCHI": "Kochi", "COCHIN/KOCHI": "Kochi",
    "CALICUT": "Kozhikode", "KOZHIKODE": "Kozhikode",
    "QUILON": "Kollam", "KOLLAM": "Kollam",
    "ALLEPPEY": "Alappuzha", "ALAPPUZHA": "Alappuzha",
    "TELLICHERRY": "Thalassery",
    "PALGHAT": "Palakkad", "PALAKKAD": "Palakkad",
    "TRICHUR": "Thrissur", "THRISSUR": "Thrissur",
    # Tamil Nadu
    "MADRAS": "Chennai", "CHENNAI": "Chennai",
    "TRICHY": "Tiruchirappalli", "TIRUCHIRAPALLI": "Tiruchirappalli",
    "TIRUCHIRAPPALLI": "Tiruchirappalli", "TRICHINOPOLY": "Tiruchirappalli",
    "TUTICORIN": "Thoothukudi", "THOOTHUKUDI": "Thoothukudi",
    "TINNEVELLY": "Tirunelveli", "TIRUNELVELI": "Tirunelveli",
    # Andhra Pradesh / Telangana
    "VIZAG": "Visakhapatnam", "VISAKHAPATNAM": "Visakhapatnam",
    "VISHAKHAPATNAM": "Visakhapatnam", "VISAKAPATNAM": "Visakhapatnam",
    "VIJAYWADA": "Vijayawada", "VIJAYAWADA": "Vijayawada",
    "RAJAHMUNDRY": "Rajamahendravaram", "RAJAMAHENDRAVARAM": "Rajamahendravaram",
    "TIRUPATHI": "Tirupati", "TIRUPATI": "Tirupati",
    "SECUNDERABAD": "Hyderabad",  # twin city, commonly consolidated
    # UP / North
    "ALLAHABAD": "Prayagraj", "PRAYAGRAJ": "Prayagraj",
    "CAWNPORE": "Kanpur", "BENARES": "Varanasi", "BANARAS": "Varanasi",
    "GURGAON": "Gurugram", "GURUGRAM": "Gurugram",
    "FARIDABAD": "Faridabad",
    "SIMLA": "Shimla", "SHIMLA": "Shimla",
    "MUSSOORIE": "Mussoorie",
    # Assam / NE
    "GAUHATI": "Guwahati", "GUWAHATI": "Guwahati",
    "SHILLONG": "Shillong",
    # Odisha
    "BHUBANESHWAR": "Bhubaneswar", "BHUBANESWAR": "Bhubaneswar",
    "CUTTACK": "Cuttack",
    # Others
    "PONDICHERRY": "Puducherry", "PONDY": "Puducherry", "PUDUCHERRY": "Puducherry",
    "PANJIM": "Panaji", "PANAJI": "Panaji",
    "NEW DELHI": "Delhi", "DELHI": "Delhi", "DELHI NCR": "Delhi NCR",
}

# City/region labels that are ALSO legitimate cities -> never "state maintained
# as city". (Delhi is a city & UT; 'Delhi NCR' is the business region label.)
VALID_CITY_REGION = {"DELHI", "NEW DELHI", "DELHI NCR"}

# City NAMES that legitimately exist in more than one state. For these, do NOT
# assert a state-city mismatch when the maintained state plausibly contains one
# of the valid options -> keep as-is / verify rather than force a wrong state.
AMBIGUOUS_MULTI_STATE = {
    "Bilaspur": {"Chhattisgarh", "Himachal Pradesh"},
    "Aurangabad": {"Maharashtra", "Bihar"},
    "Chhatrapati Sambhajinagar": {"Maharashtra", "Bihar"},
    "Hamirpur": {"Himachal Pradesh", "Uttar Pradesh"},
    "Pratapgarh": {"Uttar Pradesh", "Rajasthan"},
    "Bijapur": {"Karnataka", "Chhattisgarh"},
    "Vijayapura": {"Karnataka", "Chhattisgarh"},
    "Raigarh": {"Chhattisgarh", "Maharashtra"},
    "Balrampur": {"Uttar Pradesh", "Chhattisgarh"},
}

# ---------------------------------------------------------------------------
# 2. CITY -> (DISTRICT, STATE, GEO_ZONE)  for well-known cities.
#    Used for geographic validation & zone assignment. Canonical city keys.
# ---------------------------------------------------------------------------
# geo zones: North, South, East, West, Central, Northeast
CITY_INFO = {
    # South
    "Bengaluru": ("Bengaluru Urban", "Karnataka", "South"),
    "Mangaluru": ("Dakshina Kannada", "Karnataka", "South"),
    "Mysuru": ("Mysuru", "Karnataka", "South"),
    "Belagavi": ("Belagavi", "Karnataka", "South"),
    "Hubballi": ("Dharwad", "Karnataka", "South"),
    "Kalaburagi": ("Kalaburagi", "Karnataka", "South"),
    "Tumakuru": ("Tumakuru", "Karnataka", "South"),
    "Ballari": ("Ballari", "Karnataka", "South"),
    "Davanagere": ("Davanagere", "Karnataka", "South"),
    "Shivamogga": ("Shivamogga", "Karnataka", "South"),
    "Vijayapura": ("Vijayapura", "Karnataka", "South"),
    "Hosapete": ("Vijayanagara", "Karnataka", "South"),
    "Chikkamagaluru": ("Chikkamagaluru", "Karnataka", "South"),
    "Udupi": ("Udupi", "Karnataka", "South"),
    "Hassan": ("Hassan", "Karnataka", "South"),
    "Mandya": ("Mandya", "Karnataka", "South"),
    "Chennai": ("Chennai", "Tamil Nadu", "South"),
    "Coimbatore": ("Coimbatore", "Tamil Nadu", "South"),
    "Madurai": ("Madurai", "Tamil Nadu", "South"),
    "Tiruchirappalli": ("Tiruchirappalli", "Tamil Nadu", "South"),
    "Salem": ("Salem", "Tamil Nadu", "South"),
    "Tirunelveli": ("Tirunelveli", "Tamil Nadu", "South"),
    "Thoothukudi": ("Thoothukudi", "Tamil Nadu", "South"),
    "Erode": ("Erode", "Tamil Nadu", "South"),
    "Vellore": ("Vellore", "Tamil Nadu", "South"),
    "Thanjavur": ("Thanjavur", "Tamil Nadu", "South"),
    "Tiruppur": ("Tiruppur", "Tamil Nadu", "South"),
    "Hyderabad": ("Hyderabad", "Telangana", "South"),
    "Warangal": ("Warangal", "Telangana", "South"),
    "Karimnagar": ("Karimnagar", "Telangana", "South"),
    "Khammam": ("Khammam", "Telangana", "South"),
    "Nizamabad": ("Nizamabad", "Telangana", "South"),
    "Visakhapatnam": ("Visakhapatnam", "Andhra Pradesh", "South"),
    "Vijayawada": ("Krishna", "Andhra Pradesh", "South"),
    "Guntur": ("Guntur", "Andhra Pradesh", "South"),
    "Tirupati": ("Tirupati", "Andhra Pradesh", "South"),
    "Rajamahendravaram": ("East Godavari", "Andhra Pradesh", "South"),
    "Kakinada": ("Kakinada", "Andhra Pradesh", "South"),
    "Nellore": ("Nellore", "Andhra Pradesh", "South"),
    "Kurnool": ("Kurnool", "Andhra Pradesh", "South"),
    "Kadapa": ("Kadapa", "Andhra Pradesh", "South"),
    "Anantapur": ("Anantapur", "Andhra Pradesh", "South"),
    "Vizianagaram": ("Vizianagaram", "Andhra Pradesh", "South"),
    "Srikakulam": ("Srikakulam", "Andhra Pradesh", "South"),
    "Eluru": ("Eluru", "Andhra Pradesh", "South"),
    "Ongole": ("Prakasam", "Andhra Pradesh", "South"),
    "Thiruvananthapuram": ("Thiruvananthapuram", "Kerala", "South"),
    "Kochi": ("Ernakulam", "Kerala", "South"),
    "Kozhikode": ("Kozhikode", "Kerala", "South"),
    "Kollam": ("Kollam", "Kerala", "South"),
    "Thrissur": ("Thrissur", "Kerala", "South"),
    "Kannur": ("Kannur", "Kerala", "South"),
    "Alappuzha": ("Alappuzha", "Kerala", "South"),
    "Palakkad": ("Palakkad", "Kerala", "South"),
    "Kottayam": ("Kottayam", "Kerala", "South"),
    "Malappuram": ("Malappuram", "Kerala", "South"),
    "Puducherry": ("Puducherry", "Puducherry", "South"),
    # West
    "Mumbai": ("Mumbai", "Maharashtra", "West"),
    "Pune": ("Pune", "Maharashtra", "West"),
    "Nagpur": ("Nagpur", "Maharashtra", "West"),
    "Thane": ("Thane", "Maharashtra", "West"),
    "Nashik": ("Nashik", "Maharashtra", "West"),
    "Navi Mumbai": ("Thane", "Maharashtra", "West"),
    "Aurangabad": ("Chhatrapati Sambhajinagar", "Maharashtra", "West"),
    "Chhatrapati Sambhajinagar": ("Chhatrapati Sambhajinagar", "Maharashtra", "West"),
    "Solapur": ("Solapur", "Maharashtra", "West"),
    "Kolhapur": ("Kolhapur", "Maharashtra", "West"),
    "Amravati": ("Amravati", "Maharashtra", "West"),
    "Nanded": ("Nanded", "Maharashtra", "West"),
    "Ahmednagar": ("Ahmednagar", "Maharashtra", "West"),
    "Jalgaon": ("Jalgaon", "Maharashtra", "West"),
    "Ahmedabad": ("Ahmedabad", "Gujarat", "West"),
    "Surat": ("Surat", "Gujarat", "West"),
    "Vadodara": ("Vadodara", "Gujarat", "West"),
    "Rajkot": ("Rajkot", "Gujarat", "West"),
    "Bhavnagar": ("Bhavnagar", "Gujarat", "West"),
    "Jamnagar": ("Jamnagar", "Gujarat", "West"),
    "Gandhinagar": ("Gandhinagar", "Gujarat", "West"),
    "Anand": ("Anand", "Gujarat", "West"),
    "Junagadh": ("Junagadh", "Gujarat", "West"),
    "Panaji": ("North Goa", "Goa", "West"),
    "Margao": ("South Goa", "Goa", "West"),
    "Vasco Da Gama": ("South Goa", "Goa", "West"),
    # North
    "Delhi": ("Delhi", "Delhi", "North"),
    "Gurugram": ("Gurugram", "Haryana", "North"),
    "Faridabad": ("Faridabad", "Haryana", "North"),
    "Noida": ("Gautam Buddha Nagar", "Uttar Pradesh", "North"),
    "Greater Noida": ("Gautam Buddha Nagar", "Uttar Pradesh", "North"),
    "Ghaziabad": ("Ghaziabad", "Uttar Pradesh", "North"),
    "Lucknow": ("Lucknow", "Uttar Pradesh", "North"),
    "Kanpur": ("Kanpur Nagar", "Uttar Pradesh", "North"),
    "Varanasi": ("Varanasi", "Uttar Pradesh", "North"),
    "Agra": ("Agra", "Uttar Pradesh", "North"),
    "Prayagraj": ("Prayagraj", "Uttar Pradesh", "North"),
    "Meerut": ("Meerut", "Uttar Pradesh", "North"),
    "Bareilly": ("Bareilly", "Uttar Pradesh", "North"),
    "Aligarh": ("Aligarh", "Uttar Pradesh", "North"),
    "Moradabad": ("Moradabad", "Uttar Pradesh", "North"),
    "Gorakhpur": ("Gorakhpur", "Uttar Pradesh", "North"),
    "Jaipur": ("Jaipur", "Rajasthan", "North"),
    "Jodhpur": ("Jodhpur", "Rajasthan", "North"),
    "Udaipur": ("Udaipur", "Rajasthan", "North"),
    "Kota": ("Kota", "Rajasthan", "North"),
    "Ajmer": ("Ajmer", "Rajasthan", "North"),
    "Bikaner": ("Bikaner", "Rajasthan", "North"),
    "Chandigarh": ("Chandigarh", "Chandigarh", "North"),
    "Amritsar": ("Amritsar", "Punjab", "North"),
    "Ludhiana": ("Ludhiana", "Punjab", "North"),
    "Jalandhar": ("Jalandhar", "Punjab", "North"),
    "Patiala": ("Patiala", "Punjab", "North"),
    "Bathinda": ("Bathinda", "Punjab", "North"),
    "Mohali": ("SAS Nagar", "Punjab", "North"),
    "Dehradun": ("Dehradun", "Uttarakhand", "North"),
    "Haridwar": ("Haridwar", "Uttarakhand", "North"),
    "Rishikesh": ("Dehradun", "Uttarakhand", "North"),
    "Haldwani": ("Nainital", "Uttarakhand", "North"),
    "Shimla": ("Shimla", "Himachal Pradesh", "North"),
    "Jammu": ("Jammu", "Jammu & Kashmir", "North"),
    "Srinagar": ("Srinagar", "Jammu & Kashmir", "North"),
    "Panipat": ("Panipat", "Haryana", "North"),
    "Karnal": ("Karnal", "Haryana", "North"),
    "Hisar": ("Hisar", "Haryana", "North"),
    "Ambala": ("Ambala", "Haryana", "North"),
    "Rohtak": ("Rohtak", "Haryana", "North"),
    # East
    "Kolkata": ("Kolkata", "West Bengal", "East"),
    "Howrah": ("Howrah", "West Bengal", "East"),
    "Siliguri": ("Darjeeling", "West Bengal", "East"),
    "Durgapur": ("Paschim Bardhaman", "West Bengal", "East"),
    "Asansol": ("Paschim Bardhaman", "West Bengal", "East"),
    "Cooch Behar": ("Cooch Behar", "West Bengal", "East"),
    "Kharagpur": ("Paschim Medinipur", "West Bengal", "East"),
    "Malda": ("Malda", "West Bengal", "East"),
    "Berhampore": ("Murshidabad", "West Bengal", "East"),
    "Bardhaman": ("Purba Bardhaman", "West Bengal", "East"),
    "Barddhaman": ("Purba Bardhaman", "West Bengal", "East"),
    "Bhubaneswar": ("Khordha", "Odisha", "East"),
    "Cuttack": ("Cuttack", "Odisha", "East"),
    "Rourkela": ("Sundargarh", "Odisha", "East"),
    "Berhampur": ("Ganjam", "Odisha", "East"),
    "Sambalpur": ("Sambalpur", "Odisha", "East"),
    "Balasore": ("Balasore", "Odisha", "East"),
    "Patna": ("Patna", "Bihar", "East"),
    "Gaya": ("Gaya", "Bihar", "East"),
    "Bhagalpur": ("Bhagalpur", "Bihar", "East"),
    "Muzaffarpur": ("Muzaffarpur", "Bihar", "East"),
    "Darbhanga": ("Darbhanga", "Bihar", "East"),
    "Ranchi": ("Ranchi", "Jharkhand", "East"),
    "Jamshedpur": ("East Singhbhum", "Jharkhand", "East"),
    "Dhanbad": ("Dhanbad", "Jharkhand", "East"),
    "Bokaro": ("Bokaro", "Jharkhand", "East"),
    "Adityapur": ("Seraikela Kharsawan", "Jharkhand", "East"),
    # Central
    "Indore": ("Indore", "Madhya Pradesh", "Central"),
    "Bhopal": ("Bhopal", "Madhya Pradesh", "Central"),
    "Jabalpur": ("Jabalpur", "Madhya Pradesh", "Central"),
    "Gwalior": ("Gwalior", "Madhya Pradesh", "Central"),
    "Ujjain": ("Ujjain", "Madhya Pradesh", "Central"),
    "Sagar": ("Sagar", "Madhya Pradesh", "Central"),
    "Raipur": ("Raipur", "Chhattisgarh", "Central"),
    "Bilaspur": ("Bilaspur", "Chhattisgarh", "Central"),
    "Bhilai": ("Durg", "Chhattisgarh", "Central"),
    "Durg": ("Durg", "Chhattisgarh", "Central"),
    "Korba": ("Korba", "Chhattisgarh", "Central"),
    # Northeast
    "Guwahati": ("Kamrup Metropolitan", "Assam", "Northeast"),
    "Dibrugarh": ("Dibrugarh", "Assam", "Northeast"),
    "Silchar": ("Cachar", "Assam", "Northeast"),
    "Jorhat": ("Jorhat", "Assam", "Northeast"),
    "Tezpur": ("Sonitpur", "Assam", "Northeast"),
    "Agartala": ("West Tripura", "Tripura", "Northeast"),
    "Shillong": ("East Khasi Hills", "Meghalaya", "Northeast"),
    "Imphal": ("Imphal West", "Manipur", "Northeast"),
    "Aizawl": ("Aizawl", "Mizoram", "Northeast"),
    "Kohima": ("Kohima", "Nagaland", "Northeast"),
    "Dimapur": ("Dimapur", "Nagaland", "Northeast"),
    "Itanagar": ("Papum Pare", "Arunachal Pradesh", "Northeast"),
    "Gangtok": ("Gangtok", "Sikkim", "Northeast"),
}

# ---------------------------------------------------------------------------
# 3. LOCALITY -> PARENT CITY.  If the City column holds one of these
#    localities, it is "LOCALITY MAINTAINED AS CITY".
# ---------------------------------------------------------------------------
LOCALITY_TO_CITY = {
    # Bengaluru localities
    "HSR LAYOUT": "Bengaluru", "WHITEFIELD": "Bengaluru", "KORAMANGALA": "Bengaluru",
    "INDIRANAGAR": "Bengaluru", "INDIRA NAGAR": "Bengaluru", "JAYANAGAR": "Bengaluru",
    "MARATHAHALLI": "Bengaluru", "ELECTRONIC CITY": "Bengaluru", "BTM LAYOUT": "Bengaluru",
    "BANASHANKARI": "Bengaluru", "RAJAJINAGAR": "Bengaluru", "MALLESHWARAM": "Bengaluru",
    "YELAHANKA": "Bengaluru", "HEBBAL": "Bengaluru", "BELLANDUR": "Bengaluru",
    "SARJAPUR": "Bengaluru", "SARJAPUR ROAD": "Bengaluru", "COMMERCIAL STREET": "Bengaluru",
    "PUTTENAHALLI": "Bengaluru", "KENGERI": "Bengaluru", "RR NAGAR": "Bengaluru",
    "VIJAYANAGAR": "Bengaluru",
    # Hyderabad localities
    "KONDAPUR": "Hyderabad", "GACHIBOWLI": "Hyderabad", "MADHAPUR": "Hyderabad",
    "KUKATPALLY": "Hyderabad", "HITEC CITY": "Hyderabad", "BANJARA HILLS": "Hyderabad",
    "JUBILEE HILLS": "Hyderabad", "AMEERPET": "Hyderabad", "DILSUKHNAGAR": "Hyderabad",
    "MIYAPUR": "Hyderabad", "SECUNDERABAD": "Hyderabad", "BEGUMPET": "Hyderabad",
    "MEHDIPATNAM": "Hyderabad", "UPPAL": "Hyderabad", "LB NAGAR": "Hyderabad",
    # Mumbai localities
    "ANDHERI": "Mumbai", "BANDRA": "Mumbai", "BORIVALI": "Mumbai", "DADAR": "Mumbai",
    "GHATKOPAR": "Mumbai", "GOREGAON": "Mumbai", "KANDIVALI": "Mumbai", "MALAD": "Mumbai",
    "MULUND": "Mumbai", "POWAI": "Mumbai", "VILE PARLE": "Mumbai", "CHEMBUR": "Mumbai",
    "LOWER PAREL": "Mumbai", "COLABA": "Mumbai", "WORLI": "Mumbai",
    # Kolkata localities
    "SALT LAKE": "Kolkata", "NEW TOWN": "Kolkata", "BEHALA": "Kolkata",
    "GARIAHAT": "Kolkata", "PARK STREET": "Kolkata", "DUM DUM": "Kolkata",
    "TOLLYGUNGE": "Kolkata", "BALLYGUNGE": "Kolkata", "SALTLAKE": "Kolkata",
    # Delhi NCR localities
    "NOIDA SECTOR 18": "Noida", "CONNAUGHT PLACE": "Delhi", "SAKET": "Delhi",
    "DWARKA": "Delhi", "ROHINI": "Delhi", "JANAKPURI": "Delhi", "LAJPAT NAGAR": "Delhi",
    "KAROL BAGH": "Delhi", "RAJOURI GARDEN": "Delhi", "PITAMPURA": "Delhi",
    "VASANT KUNJ": "Delhi", "PASCHIM VIHAR": "Delhi", "GURGAON SECTOR 29": "Gurugram",
    # Chennai localities
    "T NAGAR": "Chennai", "ADYAR": "Chennai", "ANNA NAGAR": "Chennai",
    "VELACHERY": "Chennai", "TAMBARAM": "Chennai", "PORUR": "Chennai",
    "NUNGAMBAKKAM": "Chennai", "ROYAPETTAH": "Chennai", "MYLAPORE": "Chennai",
    "GUINDY": "Chennai", "OMR": "Chennai",
    # Pune localities
    "HINJEWADI": "Pune", "HINJAWADI": "Pune", "KOTHRUD": "Pune", "VIMAN NAGAR": "Pune",
    "HADAPSAR": "Pune", "BANER": "Pune", "WAKAD": "Pune", "AUNDH": "Pune",
    "KHARADI": "Pune", "PIMPRI": "Pune", "CHINCHWAD": "Pune", "MAGARPATTA": "Pune",
}

# ---------------------------------------------------------------------------
# 4. STATE canonicalisation.
#    Real-state variants -> canonical; business groupings preserved but
#    spelling-normalised.  Value = (canonical_state, is_business_grouping)
# ---------------------------------------------------------------------------
STATE_CANON = {
    "WEST BENGAL": ("West Bengal", False),
    "TAMIL NADU": ("Tamil Nadu", False), "TAMILNADU": ("Tamil Nadu", False),
    "KARNATAKA": ("Karnataka", False),
    "TELANGANA": ("Telangana", False), "TELENGANA": ("Telangana", False),
    "ANDHRA PRADESH": ("Andhra Pradesh", False), "ANDHRAPRADESH": ("Andhra Pradesh", False),
    "MAHARASHTRA": ("Maharashtra", False), "MAHARASTRA": ("Maharashtra", False),
    "GUJARAT": ("Gujarat", False),
    "KERALA": ("Kerala", False),
    "RAJASTHAN": ("Rajasthan", False),
    "MADHYA PRADESH": ("Madhya Pradesh", False),
    "ODISHA": ("Odisha", False), "ORISSA": ("Odisha", False),
    "BIHAR": ("Bihar", False),
    "JHARKHAND": ("Jharkhand", False),
    "CHHATTISGARH": ("Chhattisgarh", False), "CHHATISGARH": ("Chhattisgarh", False),
    "GOA": ("Goa", False),
    "HARYANA": ("Haryana", False),
    "PUNJAB": ("Punjab", False),
    "UTTAR PRADESH": ("Uttar Pradesh", False),
    "UTTARAKHAND": ("Uttarakhand", False),
    "HIMACHAL PRADESH": ("Himachal Pradesh", False),
    "ASSAM": ("Assam", False),
    "DELHI": ("Delhi", False),
    # Business groupings (kept, spelling normalised)
    "DELHI NCR": ("Delhi NCR", True), "DELHI-NCR": ("Delhi NCR", True), "NCR": ("Delhi NCR", True),
    "UP/UK": ("UP/UK", True), "UP-UK": ("UP/UK", True),
    "UP": ("UP", True),
    "PUNJAB/J&K/HP": ("Punjab/J&K/HP", True), "PUNJAB/J&K/HP.": ("Punjab/J&K/HP", True),
    "NORTHEAST": ("Northeast", True), "NORTH EAST": ("Northeast", True),
    "NORTH-EAST": ("Northeast", True),
    # Known ERROR: Mumbai is a city, not a state
    "MUMBAI": ("Maharashtra", False),
}

# Business grouping -> set of acceptable real states (for geo consistency)
GROUPING_MEMBERS = {
    "Delhi NCR": {"Delhi", "Haryana", "Uttar Pradesh"},
    "UP/UK": {"Uttar Pradesh", "Uttarakhand"},
    "UP": {"Uttar Pradesh", "Uttarakhand"},
    "Punjab/J&K/HP": {"Punjab", "Jammu & Kashmir", "Himachal Pradesh", "Chandigarh"},
    "Northeast": {"Assam", "Tripura", "Meghalaya", "Manipur", "Mizoram",
                  "Nagaland", "Arunachal Pradesh", "Sikkim"},
}

# State -> broad geographic zone (for rows without a city-info hit)
STATE_GEO_ZONE = {
    "Karnataka": "South", "Tamil Nadu": "South", "Telangana": "South",
    "Andhra Pradesh": "South", "Kerala": "South", "Puducherry": "South",
    "Maharashtra": "West", "Gujarat": "West", "Goa": "West",
    "Delhi": "North", "Delhi NCR": "North", "Haryana": "North", "Punjab": "North",
    "Rajasthan": "North", "Uttar Pradesh": "North", "Uttarakhand": "North",
    "Himachal Pradesh": "North", "Jammu & Kashmir": "North", "Chandigarh": "North",
    "UP/UK": "North", "UP": "North", "Punjab/J&K/HP": "North",
    "West Bengal": "East", "Odisha": "East", "Bihar": "East", "Jharkhand": "East",
    "Madhya Pradesh": "Central", "Chhattisgarh": "Central",
    "Assam": "Northeast", "Northeast": "Northeast", "Tripura": "Northeast",
    "Meghalaya": "Northeast", "Manipur": "Northeast", "Mizoram": "Northeast",
    "Nagaland": "Northeast", "Arunachal Pradesh": "Northeast", "Sikkim": "Northeast",
}
