from flask import Flask, render_template, request, jsonify
import pandas as pd
import datetime
import os

app = Flask(__name__)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Stop:
    registry = {}

    def __init__(self, shipment_obj, stop_type):
        """
        Initializes a Stop object.

        Args:
            shipment_obj (Shipment): The Shipment object associated with this stop.
            stop_type (str): The type of stop, either 'P' for Pickup or 'D' for Delivery.
        """
        if not isinstance(shipment_obj, Shipment):
            raise TypeError("shipment_obj must be an instance of the Shipment class.")
        if stop_type not in ['P', 'D']:
            raise ValueError("stop_type must be 'P' or 'D'.")

        self.shipment = shipment_obj
        self.Type = stop_type
        self.ID = f"{shipment_obj.Shipment_ID}_{stop_type}"
        self.Sequence = 0  # Default sequence, will be set when added to transport

        if self.ID in Stop.registry:
            raise ValueError(f"Stop with ID '{self.ID}' already exists.")
        Stop.registry[self.ID] = self

        # Inherit additional attributes from the Shipment object
        self.Transport = shipment_obj.Transport
        self.Weight = shipment_obj.Weight
        self.Volume = shipment_obj.Volume
        self.Ldm = shipment_obj.Ldm
        self.Content = shipment_obj.Content
        self.Units = shipment_obj.Units
        self.Unit_type = shipment_obj.Unit_type
        self.Hazardous = shipment_obj.Hazardous

        # Add new attributes
        self.Additional_Information = shipment_obj.Additional_Information
        self.Services = shipment_obj.Services

        if self.Type == 'P':
            self.Time = shipment_obj.Pickup_time
            self.Date = shipment_obj.Pickup_date
            self.Address = shipment_obj.Collection_Address
            self.City = shipment_obj.Collection_City
            self.Name = shipment_obj.Collection_Name
            self.Postal_Code = shipment_obj.Collection_Postal_Code
            self.Country = shipment_obj.Collection_Country
            self.Instructions = shipment_obj.Loading_Instructions
        elif self.Type == 'D':
            self.Time = shipment_obj.Delivery_time
            self.Date = shipment_obj.Delivery_date
            self.Address = shipment_obj.Delivery_Address
            self.City = shipment_obj.Delivery_City
            self.Name = shipment_obj.Delivery_Name
            self.Postal_Code = shipment_obj.Delivery_Postal_Code
            self.Country = shipment_obj.Delivery_Country
            self.Instructions = shipment_obj.Customer_Reference

    @classmethod
    def get_by_id(cls, stop_id):
        """
        Retrieves a Stop object by its ID.
        """
        return cls.registry.get(stop_id)

    def __repr__(self):
        return f"<Stop(ID='{self.ID}', Type='{self.Type}', City='{self.City}', Date='{self.Date}')>"

# Define the Shipment class
class Shipment:
    registry = {}

    def __init__(self, Shipment_ID, Transport, Department, Pickup_time, Pickup_date, Delivery_time, Delivery_date,
                 Collection_Name, Collection_City, Collection_Address, Collection_Postal_Code, Collection_Country,
                 Delivery_Name, Delivery_City, Delivery_Address, Delivery_Postal_Code, Delivery_Country,
                 Weight, Volume, Ldm, Content, Units, Unit_type, Hazardous, Cost,
                 Finance_Department="", Incoterm="", Customer="", Loading_Instructions="", Customer_Reference="", Additional_Information="", Services=[]):
        self.Shipment_ID = Shipment_ID
        self.Transport = Transport
        self.Department = Department
        self.Pickup_time = Pickup_time
        self.Pickup_date = Pickup_date
        self.Delivery_time = Delivery_time
        self.Delivery_date = Delivery_date
        self.Collection_Name = Collection_Name
        self.Collection_City = Collection_City
        self.Collection_Address = Collection_Address
        self.Collection_Postal_Code = Collection_Postal_Code
        self.Collection_Country = Collection_Country
        self.Delivery_Name = Delivery_Name
        self.Delivery_City = Delivery_City
        self.Delivery_Address = Delivery_Address
        self.Delivery_Postal_Code = Delivery_Postal_Code
        self.Delivery_Country = Delivery_Country
        self.Weight = Weight
        self.Volume = Volume
        self.Ldm = Ldm
        self.Content = Content
        self.Units = Units
        self.Unit_type = Unit_type
        self.Hazardous = Hazardous
        self.Cost = Cost
        self.Finance_Department = Finance_Department
        self.Incoterm = Incoterm
        self.Customer = Customer
        self.Loading_Instructions = Loading_Instructions
        self.Customer_Reference = Customer_Reference
        self.Additional_Information = Additional_Information
        self.Services = Services

        Shipment.registry[Shipment_ID] = self

        # Generate stops upon initialization
        self.stops = []
        try:
            pickup_stop = Stop(self, 'P')
            self.stops.append(pickup_stop)
        except ValueError as e:
            print(f"Warning: Could not create pickup stop for shipment {self.Shipment_ID}: {e}")

        try:
            delivery_stop = Stop(self, 'D')
            self.stops.append(delivery_stop)
        except ValueError as e:
            print(f"Warning: Could not create delivery stop for shipment {self.Shipment_ID}: {e}")

    @classmethod
    def get_by_id(cls, shipment_id):
        return cls.registry.get(shipment_id)

    def __repr__(self):
        return f"<Shipment(Shipment_ID='{self.Shipment_ID}', Department='{self.Department}', Transport='{self.Transport}')>"

class Transport:
    registry = {}

    def __init__(self, Transport_ID, department, shipments_list, Pickup_date, Delivery_date, Weight, Volume, Ldm, Cost):
        if Transport_ID in Transport.registry:
            raise ValueError(f"Transport with ID '{Transport_ID}' already exists.")
        self.Transport_ID = Transport_ID
        self.Department = department
        self.Shipments = shipments_list
        self.Pickup_date = Pickup_date
        self.Delivery_date = Delivery_date
        self.Weight = Weight
        self.Volume = Volume
        self.Ldm = Ldm
        self.Cost = Cost

        # Initialize these attributes with default values
        self.Status = 'Planning'
        self.Vehicle = ''
        self.Haulier = ''
        self.Driver = ''
        self.Trailer = ''
        self.Haulier_cost = 0.0
        self.Sale = False
        self.Sale_cost = 0.0
        self.Sheet = 1

        # Collect all Stop objects from the associated Shipments
        self.Stops = []

        Transport.registry[self.Transport_ID] = self

    @classmethod
    def get_by_id(cls, Transport_ID):
        return cls.registry.get(Transport_ID)

    def __repr__(self):
        return f"<Transport(ID='{self.Transport_ID}', Department='{self.Department}', Shipments={self.Shipments}, Weight={self.Weight}, Volume={self.Volume}, Ldm={self.Ldm}, status={self.Status}, vehicle={self.Vehicle}, Haulier={self.Haulier}, Driver={self.Driver}, Trailer={self.Trailer}, Cost={self.Cost}, Sheet={self.Sheet})>"

# Global counter
department_sequence_counters = {}

def Transport_create(list_of_shipments_df):
    if list_of_shipments_df.empty:
        raise ValueError("Input DataFrame is empty. Cannot create a Transport object.")

    # Check if any shipments are already assigned
    assigned_shipments = list_of_shipments_df[list_of_shipments_df['Transport'].notnull() & (list_of_shipments_df['Transport'] != '')]
    if not assigned_shipments.empty:
        raise ValueError("Can't create transport due to a selected shipment already being tied to a transport")

    # Get department from the first shipment
    department = list_of_shipments_df.iloc[0]['Department']

    # Get a list of Shipment_IDs for the Transport object
    Shipment_IDs = list_of_shipments_df['Shipment_ID'].tolist()

    # Calculate Pickup_date (earliest date) and Delivery_date (latest date)
    try:
        earliest_pickup_date = pd.to_datetime(list_of_shipments_df['Pickup_date']).min().date()
        latest_delivery_date = pd.to_datetime(list_of_shipments_df['Delivery_date']).max().date()
    except Exception as e:
        print(f"Date error: {e}")
        earliest_pickup_date = datetime.date.today()
        latest_delivery_date = datetime.date.today()

    # Calculate combined Weight, Volume, and Ldm
    total_weight = list_of_shipments_df['Weight'].sum()
    total_volume = list_of_shipments_df['Volume'].sum()
    total_ldm = list_of_shipments_df['Ldm'].sum()
    total_cost = list_of_shipments_df['Cost'].sum()

    # Collect stops from shipments, 'P' type before 'D' type
    transport_stops = []
    sequence = 1
    for shipment_id in Shipment_IDs:
        pickup_stop_id = f"{shipment_id}_P"
        delivery_stop_id = f"{shipment_id}_D"

        pickup_stop_obj = Stop.get_by_id(pickup_stop_id)
        delivery_stop_obj = Stop.get_by_id(delivery_stop_id)

        if pickup_stop_obj:
            pickup_stop_obj.Sequence = sequence
            transport_stops.append(pickup_stop_obj)
            sequence += 1
        if delivery_stop_obj:
            delivery_stop_obj.Sequence = sequence
            transport_stops.append(delivery_stop_obj)
            sequence += 1

    # Ensure the department has an entry in the sequence counter
    if department not in department_sequence_counters:
        department_sequence_counters[department] = 0

    # Generate a unique sequential Transport ID
    Transport_ID = None
    max_sequence_value = 9999

    while True:
        department_sequence_counters[department] += 1
        sequence_num = department_sequence_counters[department]

        if sequence_num > max_sequence_value:
            raise ValueError(f"Exceeded maximum sequential IDs ({max_sequence_value}) for department '{department}'.")

        formatted_sequence = f"{sequence_num:04d}"
        proposed_id = f"TOUR01-{formatted_sequence}"

        if Transport.get_by_id(proposed_id) is None:
            Transport_ID = proposed_id
            break

    # Create the Transport object
    new_transport = Transport(
        Transport_ID,
        department,
        Shipment_IDs,
        earliest_pickup_date,
        latest_delivery_date,
        total_weight,
        total_volume,
        total_ldm,
        total_cost
    )

    # Update the Transport_ID for each shipment object
    new_transport.Stops = transport_stops
    for Shipment_ID in Shipment_IDs:
        shipment_obj = Shipment.get_by_id(Shipment_ID)
        if shipment_obj:
            shipment_obj.Transport = new_transport.Transport_ID

    print(f"Department set to {department} and Created Transport object with ID: {new_transport.Transport_ID}")
    return new_transport

def Transport_add(transport_id, list_of_shipments_df):
    transport_obj = Transport.get_by_id(transport_id)
    if not transport_obj:
        return None

    # Filter shipments that have Transport set to None or empty
    available_shipments = list_of_shipments_df[list_of_shipments_df['Transport'].isnull() | (list_of_shipments_df['Transport'] == '')]
    if available_shipments.empty:
        print("No available shipments to add.")
        return transport_obj

    # Add shipment IDs to the transport's Shipments list
    new_shipment_ids = available_shipments['Shipment_ID'].tolist()
    transport_obj.Shipments.extend(new_shipment_ids)

    # Update totals
    transport_obj.Weight += available_shipments['Weight'].sum()
    transport_obj.Volume += available_shipments['Volume'].sum()
    transport_obj.Ldm += available_shipments['Ldm'].sum()
    transport_obj.Cost += available_shipments['Cost'].sum()

    # Update Pickup_date and Delivery_date if necessary
    earliest_pickup = pd.to_datetime(available_shipments['Pickup_date']).min().date()
    latest_delivery = pd.to_datetime(available_shipments['Delivery_date']).max().date()
    if earliest_pickup < transport_obj.Pickup_date:
        transport_obj.Pickup_date = earliest_pickup
    if latest_delivery > transport_obj.Delivery_date:
        transport_obj.Delivery_date = latest_delivery

    # Collect stops
    for shipment_id in new_shipment_ids:
        pickup_stop_id = f"{shipment_id}_P"
        delivery_stop_id = f"{shipment_id}_D"
        pickup_stop_obj = Stop.get_by_id(pickup_stop_id)
        delivery_stop_obj = Stop.get_by_id(delivery_stop_id)
        if pickup_stop_obj:
            transport_obj.Stops.append(pickup_stop_obj)
        if delivery_stop_obj:
            transport_obj.Stops.append(delivery_stop_obj)
    
    # Update sequence numbers for all stops
    for idx, stop in enumerate(transport_obj.Stops, start=1):
        stop.Sequence = idx

    # Update shipment objects
    for shipment_id in new_shipment_ids:
        shipment_obj = Shipment.get_by_id(shipment_id)
        if shipment_obj:
            shipment_obj.Transport = transport_obj.Transport_ID

    print(f"Added shipments {new_shipment_ids} to transport {transport_obj.Transport_ID}")
    return transport_obj

def Transport_remove(shipment_ids):
    """
    Removes one or more shipments from a transport and updates the transport's metrics.
    All shipments must be assigned to the same transport.
    """
    if not shipment_ids:
        raise ValueError("No shipment IDs provided.")
    
    # Get the transport ID from the shipments and verify all have the same transport
    transport_id = None
    for shipment_id in shipment_ids:
        shipment_obj = Shipment.get_by_id(shipment_id)
        if not shipment_obj:
            raise ValueError(f"Shipment '{shipment_id}' not found.")
        
        if transport_id is None:
            transport_id = shipment_obj.Transport
            if not transport_id:
                raise ValueError(f"Shipment '{shipment_id}' is not assigned to any transport.")
        else:
            if shipment_obj.Transport != transport_id:
                raise ValueError(f"All shipments must be assigned to the same transport. Found '{shipment_obj.Transport}' and '{transport_id}'.")
    
    # Get the transport object
    transport = Transport.get_by_id(transport_id)
    if not transport:
        raise ValueError(f"Transport '{transport_id}' not found.")

    removed_count = 0
    for shipment_id in shipment_ids:
        if shipment_id not in transport.Shipments:
            continue

        # Retrieve the corresponding Shipment object before removing its ID from transport.Shipments
        shipment_to_remove = Shipment.get_by_id(shipment_id)

        # Remove the shipment_id from the Transport object's Shipments list.
        transport.Shipments.remove(shipment_id)

        if shipment_to_remove:
            # Set its Transport attribute to None
            shipment_to_remove.Transport = None

            # Subtract the Weight, Volume, and Ldm of the removed Shipment object
            transport.Weight -= shipment_to_remove.Weight
            transport.Volume -= shipment_to_remove.Volume
            transport.Ldm -= shipment_to_remove.Ldm
            transport.Cost -= shipment_to_remove.Cost

            # Identify the specific Stop objects to be removed using their unique IDs
            stops_to_remove_objs = []
            pickup_stop_id = f"{shipment_id}_P"
            delivery_stop_id = f"{shipment_id}_D"

            pickup_stop_obj = Stop.get_by_id(pickup_stop_id)
            delivery_stop_obj = Stop.get_by_id(delivery_stop_id)

            if pickup_stop_obj:
                stops_to_remove_objs.append(pickup_stop_obj)
            if delivery_stop_obj:
                stops_to_remove_objs.append(delivery_stop_obj)

            # Create a new list of stops, excluding the identified Stop objects
            new_stops = []
            for stop in transport.Stops:
                # Check if the current stop object is one of the specific objects we want to remove
                if stop not in stops_to_remove_objs:
                    new_stops.append(stop)
            transport.Stops = new_stops

        removed_count += 1
    
    # Update sequence numbers for all remaining stops
    for idx, stop in enumerate(transport.Stops, start=1):
        stop.Sequence = idx

    if removed_count > 0:
        print(f"Successfully removed {removed_count} shipment(s) from Transport '{transport_id}'.")
        print(f"Updated Transport '{transport_id}' details: Weight={transport.Weight}, Volume={transport.Volume}, Ldm={transport.Ldm}, Cost={transport.Cost}, Stops={transport.Stops}")
    
    return transport

# Load data
shipments_df = pd.read_csv(os.path.join(BASE_DIR, 'df_shipments.csv'))
# Convert postal codes to integers to avoid decimal display
# Strip spaces first before converting
if 'Collection_Postal_Code' in shipments_df.columns:
    shipments_df['Collection_Postal_Code'] = shipments_df['Collection_Postal_Code'].astype(str).str.replace(' ', '', regex=False)
    shipments_df['Collection_Postal_Code'] = pd.to_numeric(shipments_df['Collection_Postal_Code'], errors='coerce').fillna(0).astype(int)
if 'Delivery_Postal_Code' in shipments_df.columns:
    shipments_df['Delivery_Postal_Code'] = shipments_df['Delivery_Postal_Code'].astype(str).str.replace(' ', '', regex=False)
    shipments_df['Delivery_Postal_Code'] = pd.to_numeric(shipments_df['Delivery_Postal_Code'], errors='coerce').fillna(0).astype(int)
trucks_df = pd.read_csv(os.path.join(BASE_DIR, 'df_trucks.csv'))
if 'Sheet' not in trucks_df.columns:
    trucks_df['Sheet'] = 1
# Generate random times between 06:00 and 20:00 for each truck
if 'Time' not in trucks_df.columns or trucks_df['Time'].isnull().any():
    import random
    def generate_random_time():
        hour = random.randint(6, 19)
        minute = random.choice([0, 15, 30, 45])
        return f"{hour:02d}:{minute:02d}"
    trucks_df['Time'] = [generate_random_time() for _ in range(len(trucks_df))]
# Generate random dates for current week (weekdays only)
if 'Date' not in trucks_df.columns or trucks_df['Date'].isnull().any():
    import random
    today = datetime.date.today()
    # Find Monday of current week
    monday = today - datetime.timedelta(days=today.weekday())
    # Generate list of weekdays (Mon-Fri) for current week
    weekdays = [monday + datetime.timedelta(days=i) for i in range(5)]
    trucks_df['Date'] = [random.choice(weekdays) for _ in range(len(trucks_df))]
trailers_df = pd.read_csv(os.path.join(BASE_DIR, 'df_trailers.csv'))

# Combine trucks and trailers as transports
transports_df = trucks_df.copy()

# Initialize Shipment objects
for _, row in shipments_df.iterrows():
    Shipment(
        row['Shipment_ID'], row['Transport'], row['Department'], row['Pickup_time'], row['Pickup_date'],
        row['Delivery_time'], row['Delivery_date'], row['Collection_Name'], row['Collection_City'],
        row['Collection_Address'], row['Collection_Postal_Code'], row['Collection_Country'],
        row['Delivery_Name'], row['Delivery_City'], row['Delivery_Address'], row['Delivery_Postal_Code'],
        row['Delivery_Country'], row['Weight'], row['Volume'], row['Ldm'],
        row['Content'], row['Units'], row['Unit_type'], row['Hazardous'], row['Cost'],
        row.get('Finance_Department', ''), row.get('Incoterm', ''), row.get('Customer', ''),
        row.get('Loading_Instructions', ''), row.get('Customer_Reference', ''), 
        row.get('Additional_Information', ''), row.get('Services', [])
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shipments')
def shipments():
    # Start with the full dataframe
    filtered_df = shipments_df.copy()
    
    # Apply department filter (defaults to KDEGR)
    department = request.args.get('department', 'KDEGR').strip()
    if department and department != 'ALL':
        filtered_df = filtered_df[filtered_df['Department'] == department]
    
    # Apply unassigned filter by default, unless explicitly set to 'all'
    filter_param = request.args.get('filter', 'unassigned')
    filter_unassigned = filter_param == 'unassigned'
    if filter_unassigned:
        filtered_df = filtered_df[filtered_df['Transport'].isnull() | (filtered_df['Transport'] == '')]
    
    # Apply search filters
    shipment_id = request.args.get('shipment_id', '').strip()
    if shipment_id:
        filtered_df = filtered_df[filtered_df['Shipment_ID'].str.contains(shipment_id, case=False, na=False)]
    
    # Parse postal code ranges with optional country codes
    # Supports: "BE:2700-3500", "NL:1000-2000,BE:2700-3500", "BE", or "2700-3500"
    def parse_pc_ranges(pc_string, column_name, country_column_name):
        if not pc_string:
            return filtered_df
        
        ranges = pc_string.split(',')
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        
        for range_str in ranges:
            range_str = range_str.strip()
            country_code = None
            postal_range = None
            
            # Check if country code is specified (e.g., "BE:2700-3500" or just "BE")
            if ':' in range_str:
                parts = range_str.split(':', 1)
                country_code = parts[0].strip().upper()
                postal_range = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            else:
                # Check if it's just a country code (2-3 letters) or a postal code range
                if range_str.replace('-', '').replace(' ', '').isalpha() and len(range_str) <= 3:
                    country_code = range_str.upper()
                    postal_range = None
                else:
                    postal_range = range_str
            
            # Build country mask
            country_mask = pd.Series([True] * len(filtered_df), index=filtered_df.index)
            if country_code:
                country_mask = (filtered_df[country_column_name].str.upper() == country_code)
            
            # Parse postal code range
            if postal_range and '-' in postal_range:
                parts = postal_range.split('-')
                if len(parts) == 2:
                    try:
                        min_val = int(parts[0].strip())
                        max_val = int(parts[1].strip())
                        # Convert postal codes to int for comparison, stripping spaces first
                        pc_stripped = filtered_df[column_name].astype(str).str.replace(' ', '', regex=False)
                        pc_as_int = pd.to_numeric(pc_stripped, errors='coerce')
                        mask |= country_mask & (pc_as_int >= min_val) & (pc_as_int <= max_val)
                    except ValueError:
                        pass
            elif country_code and not postal_range:
                # Just country code without postal code range
                mask |= country_mask
        
        return filtered_df[mask] if mask.any() else filtered_df
    
    collection_pc = request.args.get('collection_pc', '').strip()
    if collection_pc:
        filtered_df = parse_pc_ranges(collection_pc, 'Collection_Postal_Code', 'Collection_Country')
    
    delivery_pc = request.args.get('delivery_pc', '').strip()
    if delivery_pc:
        filtered_df = parse_pc_ranges(delivery_pc, 'Delivery_Postal_Code', 'Delivery_Country')
    
    # Apply date range filter (from start_date to start_date + X days, negative values go backwards)
    # Default to 0 days if not specified (show only today)
    date_range_days = request.args.get('date_range_days', '0').strip()
    start_date_str = request.args.get('start_date', '').strip()
    
    if date_range_days:
        try:
            days = int(date_range_days)
            if start_date_str:
                start_date = pd.to_datetime(start_date_str).date()
            else:
                start_date = datetime.date.today()
            
            if days >= 0:
                # Positive range: from start_date to start_date + days
                end_date = start_date + datetime.timedelta(days=days)
                filtered_df = filtered_df[
                    (pd.to_datetime(filtered_df['Pickup_date']).dt.date >= start_date) &
                    (pd.to_datetime(filtered_df['Pickup_date']).dt.date <= end_date)
                ]
            else:
                # Negative range: from start_date + days to start_date
                end_date = start_date
                start_date = start_date + datetime.timedelta(days=days)
                filtered_df = filtered_df[
                    (pd.to_datetime(filtered_df['Pickup_date']).dt.date >= start_date) &
                    (pd.to_datetime(filtered_df['Pickup_date']).dt.date <= end_date)
                ]
        except ValueError:
            pass
    
    shipments_list = filtered_df.to_dict('records')
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('shipments.html', shipments=shipments_list, filter_unassigned=filter_unassigned, today_date=today_date)

@app.route('/transports')
def transports():
    # Start with all transports
    all_transports = list(Transport.registry.values())
    filtered_transports = all_transports.copy()
    
    # Apply department filter (defaults to KDEGR)
    department = request.args.get('department', 'KDEGR').strip()
    if department and department != 'ALL':
        filtered_transports = [t for t in filtered_transports if t.Department == department]
    
    # Apply search filters
    transport_id = request.args.get('transport_id', '').strip()
    if transport_id:
        filtered_transports = [t for t in filtered_transports if transport_id.lower() in t.Transport_ID.lower()]
    
    # Parse postal code ranges with optional country codes for first and last stop
    # Supports: "BE:2700-3500", "NL:1000-2000,BE:2700-3500", "BE", or "2700-3500"
    def matches_pc_ranges(pc_value, country_value, pc_string):
        if not pc_string:
            return True
        if pc_value is None:
            return False
        
        # Convert pc_value to int if it's a string, stripping spaces first
        try:
            pc_value_str = str(pc_value).replace(' ', '')
            pc_value_int = int(pc_value_str)
        except (ValueError, TypeError):
            return False
        
        ranges = pc_string.split(',')
        for range_str in ranges:
            range_str = range_str.strip()
            country_code = None
            postal_range = None
            
            # Check if country code is specified (e.g., "BE:2700-3500" or just "BE")
            if ':' in range_str:
                parts = range_str.split(':', 1)
                country_code = parts[0].strip().upper()
                postal_range = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            else:
                # Check if it's just a country code (2-3 letters) or a postal code range
                if range_str.replace('-', '').replace(' ', '').isalpha() and len(range_str) <= 3:
                    country_code = range_str.upper()
                    postal_range = None
                else:
                    postal_range = range_str
            
            # Check country match
            country_matches = True
            if country_code:
                country_matches = (country_value and country_value.upper() == country_code)
            
            if not country_matches:
                continue
            
            # Parse postal code range
            if postal_range and '-' in postal_range:
                parts = postal_range.split('-')
                if len(parts) == 2:
                    try:
                        min_val = int(parts[0].strip())
                        max_val = int(parts[1].strip())
                        if min_val <= pc_value_int <= max_val:
                            return True
                    except ValueError:
                        pass
            elif country_code and not postal_range:
                # Just country code without postal code range
                return True
        return False
    
    collection_pc = request.args.get('collection_pc', '').strip()
    if collection_pc:
        filtered_transports = [t for t in filtered_transports 
                              if t.Stops and matches_pc_ranges(
                                  t.Stops[0].Postal_Code if t.Stops else None,
                                  t.Stops[0].Country if t.Stops else None,
                                  collection_pc)]
    
    delivery_pc = request.args.get('delivery_pc', '').strip()
    if delivery_pc:
        filtered_transports = [t for t in filtered_transports 
                              if t.Stops and matches_pc_ranges(
                                  t.Stops[-1].Postal_Code if t.Stops else None,
                                  t.Stops[-1].Country if t.Stops else None,
                                  delivery_pc)]
    
    # Apply date range filter
    date_range_days = request.args.get('date_range_days', '').strip()
    start_date_str = request.args.get('start_date', '').strip()
    
    if date_range_days:
        try:
            days = int(date_range_days)
            if start_date_str:
                start_date = pd.to_datetime(start_date_str).date()
            else:
                start_date = datetime.date.today()
            
            if days >= 0:
                end_date = start_date + datetime.timedelta(days=days)
                filtered_transports = [t for t in filtered_transports 
                                      if hasattr(t, 'Pickup_date') and start_date <= t.Pickup_date <= end_date]
            else:
                end_date = start_date
                start_date = start_date + datetime.timedelta(days=days)
                filtered_transports = [t for t in filtered_transports 
                                      if hasattr(t, 'Pickup_date') and start_date <= t.Pickup_date <= end_date]
        except (ValueError, AttributeError, TypeError):
            pass
    
    # Prepare transport data with additional stop information
    transports_list = []
    for transport in filtered_transports:
        first_stop = transport.Stops[0] if transport.Stops else None
        last_stop = transport.Stops[-1] if transport.Stops else None
        transport_data = {
            'Transport_ID': transport.Transport_ID,
            'Ldm': transport.Ldm,
            'Weight': transport.Weight,
            'Cost': transport.Cost,
            'Sale': transport.Sale,
            'first_stop_date': first_stop.Date if first_stop else '',
            'first_stop_time': first_stop.Time if first_stop else '',
            'first_collection_country': first_stop.shipment.Collection_Country if first_stop else '',
            'first_collection_postal': first_stop.shipment.Collection_Postal_Code if first_stop else '',
            'last_stop_date': last_stop.Date if last_stop else '',
            'last_stop_time': last_stop.Time if last_stop else '',
            'last_delivery_country': last_stop.shipment.Delivery_Country if last_stop else '',
            'last_delivery_postal': last_stop.shipment.Delivery_Postal_Code if last_stop else ''
        }
        transports_list.append(transport_data)
    
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('transports.html', transports=transports_list, today_date=today_date)

@app.route('/details/<type>/<id>')
def details(type, id):
    if type == 'shipment':
        shipment = shipments_df[shipments_df['Shipment_ID'] == id].to_dict('records')[0]
        # Create stops
        stops = [
            {
                'Type': 'Pickup',
                'Time': shipment['Pickup_time'],
                'Date': shipment['Pickup_date'],
                'Name': shipment['Collection_Name'],
                'City': shipment['Collection_City'],
                'Address': shipment['Collection_Address'],
                'Postal_Code': shipment['Collection_Postal_Code']
            },
            {
                'Type': 'Delivery',
                'Time': shipment['Delivery_time'],
                'Date': shipment['Delivery_date'],
                'Name': shipment['Delivery_Name'],
                'City': shipment['Delivery_City'],
                'Address': shipment['Delivery_Address'],
                'Postal_Code': shipment['Delivery_Postal_Code']
            }
        ]
        return render_template('details.html', item=shipment, stops=stops, item_type='shipment')
    elif type == 'transport':
        transport = Transport.get_by_id(id)
        if transport:
            stops = transport.Stops
            return render_template('details.html', item=transport, stops=stops, item_type='transport')
        else:
            return "Transport not found", 404

@app.route('/create_transport', methods=['POST'])
def create_transport():
    try:
        data = request.get_json()
        shipment_ids = data['shipments']
        print("Creating transport for", shipment_ids)
        selected_df = shipments_df[shipments_df['Shipment_ID'].isin(shipment_ids)]
        print("Selected df shape", selected_df.shape)
        transport = Transport_create(selected_df)
        print("Transport created", transport.Transport_ID)
        # Update shipments_df
        for sid in shipment_ids:
            shipments_df.loc[shipments_df['Shipment_ID'] == sid, 'Transport'] = transport.Transport_ID
        return jsonify({'message': f'Transport {transport.Transport_ID} created'})
    except Exception as e:
        print("Error:", e)
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/add_shipment', methods=['POST'])
def add_shipment():
    try:
        data = request.get_json()
        transport_id = data['transport']
        shipment_ids = data['shipments']
        selected_df = shipments_df[shipments_df['Shipment_ID'].isin(shipment_ids)]
        transport = Transport_add(transport_id, selected_df)
        if transport:
            # Update shipments_df
            for sid in shipment_ids:
                shipments_df.loc[shipments_df['Shipment_ID'] == sid, 'Transport'] = transport.Transport_ID
            return jsonify({'message': f'Shipments added to transport {transport.Transport_ID}'})
        else:
            return jsonify({'message': 'Transport not found'}), 404
    except Exception as e:
        print("Error in add_shipment:", e)
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/remove_shipment', methods=['POST'])
def remove_shipment():
    try:
        data = request.get_json()
        shipment_ids = data['shipments']
        transport = Transport_remove(shipment_ids)
        if transport:
            # Update shipments_df to set Transport to None for removed shipments
            for sid in shipment_ids:
                shipments_df.loc[shipments_df['Shipment_ID'] == sid, 'Transport'] = None
            return jsonify({'message': f'Shipments removed from transport {transport.Transport_ID}'})
        else:
            return jsonify({'message': 'Transport not found'}), 404
    except Exception as e:
        print("Error in remove_shipment:", e)
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/sell_shipment_transport', methods=['POST'])
def sell_shipment_transport():
    try:
        data = request.get_json()
        shipment_ids = data.get('shipments', [])
        transport_id = data.get('transport', None)
        sale_cost = data.get('sale_cost', 0.0)
        
        if transport_id:
            # Set Sale = True for the selected transport
            transport = Transport.get_by_id(transport_id)
            if transport:
                transport.Sale = True
                transport.Sale_cost = sale_cost
                return jsonify({'message': f'Transport {transport_id} marked for sale with cost {sale_cost}'})
            else:
                return jsonify({'message': 'Transport not found'}), 404
        elif shipment_ids:
            # Create a transport from shipments and set Sale = True
            selected_df = shipments_df[shipments_df['Shipment_ID'].isin(shipment_ids)]
            transport = Transport_create(selected_df)
            transport.Sale = True
            transport.Sale_cost = sale_cost
            # Update shipments_df
            for sid in shipment_ids:
                shipments_df.loc[shipments_df['Shipment_ID'] == sid, 'Transport'] = transport.Transport_ID
            return jsonify({'message': f'Transport {transport.Transport_ID} created and marked for sale with cost {sale_cost}'})
        else:
            return jsonify({'message': 'No shipments or transport selected'}), 400
    except Exception as e:
        print("Error in sell_shipment_transport:", e)
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/get_transport_info')
def get_transport_info():
    transport_id = request.args.get('transport_id', '')
    if transport_id:
        transport = Transport.get_by_id(transport_id)
        if transport:
            return jsonify({
                'transport_id': transport.Transport_ID,
                'shipments': transport.Shipments
            })
    return jsonify({'error': 'Transport not found'}), 404

@app.route('/planning')
def planning():
    # Get filter parameters
    department = request.args.get('department', 'KDEGR').strip()
    start_date_str = request.args.get('start_date', '').strip()
    date_range_days = request.args.get('date_range_days', '0').strip()
    
    # Filter trucks by department
    if department and department != 'ALL':
        filtered_trucks_df = trucks_df[trucks_df['Department'] == department].copy()
    else:
        filtered_trucks_df = trucks_df.copy()
    
    # Apply date range filter to trucks
    if date_range_days:
        try:
            days = int(date_range_days)
            if start_date_str:
                start_date = pd.to_datetime(start_date_str).date()
            else:
                start_date = datetime.date.today()
            
            if days >= 0:
                end_date = start_date + datetime.timedelta(days=days)
            else:
                end_date = start_date
                start_date = start_date + datetime.timedelta(days=days)
            
            # Filter trucks by date range
            filtered_trucks_df['Date'] = pd.to_datetime(filtered_trucks_df['Date']).dt.date
            filtered_trucks_df = filtered_trucks_df[
                (filtered_trucks_df['Date'] >= start_date) & 
                (filtered_trucks_df['Date'] <= end_date)
            ]
        except (ValueError, AttributeError, TypeError, KeyError):
            pass
    
    # Filter out trucks that already have a Transport assigned
    filtered_trucks_df = filtered_trucks_df[
        (filtered_trucks_df['Transport'].isna()) | 
        (filtered_trucks_df['Transport'] == '')
    ]
    
    trucks_list = filtered_trucks_df.to_dict('records')
    
    # Start with all transports
    all_transports = list(Transport.registry.values())
    filtered_transports = all_transports.copy()
    
    # Apply department filter
    if department and department != 'ALL':
        filtered_transports = [t for t in filtered_transports if t.Department == department]
    
    # Filter to only show transports with status "Planning"
    filtered_transports = [t for t in filtered_transports if t.Status == 'Planning']
    
    # Apply date range filter to transports
    if date_range_days:
        try:
            days = int(date_range_days)
            if start_date_str:
                start_date = pd.to_datetime(start_date_str).date()
            else:
                start_date = datetime.date.today()
            
            if days >= 0:
                end_date = start_date + datetime.timedelta(days=days)
                filtered_transports = [t for t in filtered_transports 
                                      if hasattr(t, 'Pickup_date') and start_date <= t.Pickup_date <= end_date]
            else:
                end_date = start_date
                start_date = start_date + datetime.timedelta(days=days)
                filtered_transports = [t for t in filtered_transports 
                                      if hasattr(t, 'Pickup_date') and start_date <= t.Pickup_date <= end_date]
        except (ValueError, AttributeError, TypeError):
            pass
    
    # Combine transports and trucks into a single table
    combined_list = []
    
    # Add transports to combined list
    for transport in filtered_transports:
        first_stop = transport.Stops[0] if transport.Stops else None
        location_str = ''
        if first_stop:
            country = first_stop.Country if first_stop.Country else ''
            postal = str(first_stop.Postal_Code) if first_stop.Postal_Code else ''
            city = first_stop.City if first_stop.City else ''
            location_str = f"{country} {postal} {city}"
        combined_item = {
            'Type': 'Transport',
            'ID': transport.Transport_ID,
            'Location': location_str,
            'Time': first_stop.Time if first_stop else '',
            'Date': transport.Pickup_date,
            'License_Plate': transport.Vehicle,
            'Driver': transport.Driver,
            'Trailer': transport.Trailer if transport.Trailer else '',
            'Haulier': transport.Haulier,
            'Weight': transport.Weight,
            'Ldm': transport.Ldm,
            'Cost': transport.Cost,
            'Sale': transport.Sale,
            'Department': transport.Department
        }
        combined_list.append(combined_item)
    
    # Add trucks to combined list
    for truck in trucks_list:
        # Parse and format location
        location_raw = truck.get('Location', '')
        location_str = ''
        if location_raw:
            if ',' in location_raw:
                # Format: "City, PostalCode, CountryCode" -> "CountryCode PostalCode City"
                parts = [p.strip() for p in location_raw.split(',')]
                if len(parts) == 3:
                    city, postal, country = parts
                    location_str = f"{country} {postal} {city}"
                else:
                    location_str = location_raw
            elif '-' in location_raw:
                # Format: "DK-9300" -> "DK 9300"
                parts = location_raw.split('-')
                if len(parts) == 2:
                    location_str = f"{parts[0]} {parts[1]}"
                else:
                    location_str = location_raw
            else:
                location_str = location_raw
        
        combined_item = {
            'Type': 'Truck',
            'ID': truck.get('License_plate', ''),
            'Location': location_str,
            'Time': truck.get('Time', ''),
            'Date': truck.get('Date', ''),
            'License_Plate': truck.get('License_plate', ''),
            'Driver': truck.get('Driver', ''),
            'Trailer': truck.get('Trailer', '') if pd.notna(truck.get('Trailer')) else '',
            'Haulier': truck.get('Haulier', ''),
            'Weight': '',
            'Ldm': '',
            'Cost': '',
            'Sale': '',
            'Department': truck.get('Department', ''),
            'Last_transport': truck.get('Last_transport', '')
        }
        combined_list.append(combined_item)
    
    # Sort by Time descending
    combined_list.sort(key=lambda x: x['Time'] if x['Time'] else '', reverse=True)
    
    # Get available trailers based on department filter and open_pool checkbox
    open_pool_filter = request.args.get('open_pool', 'false').lower() == 'true'
    if open_pool_filter:
        # When checked: show all trailers with Open_pool == True (ignore department)
        available_trailers = trailers_df[
            trailers_df['Open_pool'] == True
        ]
    else:
        # When unchecked: show trailers from filtered department with Open_pool == False
        if department and department != 'ALL':
            available_trailers = trailers_df[
                (trailers_df['Department'] == department) & 
                (trailers_df['Open_pool'] == False)
            ]
        else:
            available_trailers = trailers_df[
                trailers_df['Open_pool'] == False
            ]
    
    # Convert to list of license plates for the template
    trailers_list = available_trailers['License_plate'].tolist()
    
    return render_template('planning.html', combined_items=combined_list, available_trailers=trailers_list, current_department=department)

@app.route('/planning/stops/<type>/<id>')
def planning_stops(type, id):
    if type == 'transport':
        transport = Transport.get_by_id(id)
        if transport:
            # Return full transport overview data
            transport_data = {
                'Transport_ID': transport.Transport_ID,
                'Department': transport.Department,
                'Shipments': transport.Shipments,
                'Pickup_date': str(transport.Pickup_date) if transport.Pickup_date else '',
                'Delivery_date': str(transport.Delivery_date) if transport.Delivery_date else '',
                'Weight': float(transport.Weight) if transport.Weight else 0,
                'Volume': float(transport.Volume) if transport.Volume else 0,
                'Ldm': float(transport.Ldm) if transport.Ldm else 0,
                'Cost': float(transport.Cost) if transport.Cost else 0,
                'Status': transport.Status,
                'Vehicle': transport.Vehicle,
                'Haulier': transport.Haulier,
                'Driver': transport.Driver,
                'Trailer': transport.Trailer
            }
            
            # Get stops data
            stops_data = []
            if transport.Stops:
                for stop in transport.Stops:
                    stops_data.append({
                        'ID': stop.ID,
                        'Type': stop.Type,
                        'Sequence': int(stop.Sequence) if stop.Sequence else 0,
                        'Shipment_ID': stop.shipment.Shipment_ID if stop.shipment else '',
                        'Country': stop.Country,
                        'Postal_Code': int(stop.Postal_Code) if stop.Postal_Code else 0,
                        'City': stop.City,
                        'Name': stop.Name,
                        'Address': stop.Address,
                        'Date': str(stop.Date) if stop.Date else '',
                        'Time': stop.Time,
                        'Weight': float(stop.Weight) if stop.Weight else 0,
                        'Volume': float(stop.Volume) if stop.Volume else 0,
                        'Ldm': float(stop.Ldm) if stop.Ldm else 0
                    })
            
            return jsonify({'transport': transport_data, 'stops': stops_data})
    return jsonify({'transport': None, 'stops': []})

@app.route('/reorder_stops', methods=['POST'])
def reorder_stops():
    try:
        data = request.get_json()
        transport_id = data['transport_id']
        stop_id = data['stop_id']
        new_sequence = int(data['new_sequence'])
        
        transport = Transport.get_by_id(transport_id)
        if not transport:
            return jsonify({'error': 'Transport not found'}), 404
        
        # Find the stop to move
        stop_to_move = None
        old_sequence = 0
        for stop in transport.Stops:
            if stop.ID == stop_id:
                stop_to_move = stop
                old_sequence = stop.Sequence
                break
        
        if not stop_to_move:
            return jsonify({'error': 'Stop not found'}), 404
        
        # Validate new sequence
        if new_sequence < 1 or new_sequence > len(transport.Stops):
            return jsonify({'error': f'Invalid sequence number. Must be between 1 and {len(transport.Stops)}'}), 400
        
        # Update sequence numbers without changing positions
        if new_sequence != old_sequence:
            # If moving up (increasing sequence number)
            if new_sequence > old_sequence:
                # All stops between old and new position shift down by 1
                for stop in transport.Stops:
                    if stop.Sequence > old_sequence and stop.Sequence <= new_sequence:
                        stop.Sequence -= 1
            # If moving down (decreasing sequence number)
            else:
                # All stops between new and old position shift up by 1
                for stop in transport.Stops:
                    if stop.Sequence >= new_sequence and stop.Sequence < old_sequence:
                        stop.Sequence += 1
            
            # Set the new sequence for the moved stop
            stop_to_move.Sequence = new_sequence
        
        # Return updated stops data
        stops_data = []
        for stop in transport.Stops:
            stops_data.append({
                'ID': stop.ID,
                'Type': stop.Type,
                'Sequence': stop.Sequence,
                'Shipment_ID': stop.shipment.Shipment_ID,
                'Country': stop.Country,
                'Postal_Code': stop.Postal_Code,
                'City': stop.City
            })
        
        return jsonify({'message': 'Stop reordered successfully', 'stops': stops_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_truck_time', methods=['POST'])
def update_truck_time():
    try:
        data = request.json
        license_plate = data.get('license_plate')
        new_time = data.get('time')
        
        if not license_plate:
            return jsonify({'success': False, 'error': 'License plate required'}), 400
        
        # Update in the DataFrame
        global trucks_df
        mask = trucks_df['License_plate'] == license_plate
        if not mask.any():
            return jsonify({'success': False, 'error': 'Truck not found'}), 404
        
        trucks_df.loc[mask, 'Time'] = new_time
        
        # Save to CSV
        trucks_df.to_csv('Backend_Mobility/df_trucks.csv', index=False)
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_transport_time', methods=['POST'])
def update_transport_time():
    try:
        data = request.json
        transport_id = data.get('transport_id')
        new_time = data.get('time')
        
        if not transport_id:
            return jsonify({'success': False, 'error': 'Transport ID required'}), 400
        
        # Get the transport object
        transport = Transport.get_by_id(transport_id)
        if not transport:
            return jsonify({'success': False, 'error': 'Transport not found'}), 404
        
        # Update the time for the first stop (which is used for display)
        if transport.Stops and len(transport.Stops) > 0:
            transport.Stops[0].Time = new_time
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/assign_transport', methods=['POST'])
def assign_transport():
    try:
        data = request.json
        transport_id = data.get('transport_id')
        truck_id = data.get('truck_id')
        
        if not transport_id or not truck_id:
            return jsonify({'success': False, 'error': 'Both transport_id and truck_id are required'}), 400
        
        # Get the transport object
        transport = Transport.get_by_id(transport_id)
        if not transport:
            return jsonify({'success': False, 'error': 'Transport not found'}), 404
        
        # Check if transport already has a vehicle
        if transport.Vehicle != "":
            return jsonify({'success': False, 'error': 'Transport already has a vehicle assigned'}), 400
        
        # Get truck from DataFrame
        global trucks_df
        truck_mask = trucks_df['License_plate'] == truck_id
        if not truck_mask.any():
            return jsonify({'success': False, 'error': 'Truck not found'}), 404
        
        truck_row = trucks_df[truck_mask].iloc[0]
        
        # Update Transport object (convert pandas types to Python native types)
        transport.Vehicle = str(truck_row['License_plate']) if pd.notna(truck_row['License_plate']) else ""
        transport.Driver = str(truck_row['Driver']) if pd.notna(truck_row['Driver']) else ""
        if transport.Trailer == "":
            transport.Trailer = str(truck_row['Trailer']) if pd.notna(truck_row['Trailer']) else ""
        transport.Haulier = str(truck_row['Haulier']) if pd.notna(truck_row['Haulier']) else ""
        
        # Update Truck in DataFrame
        trucks_df.loc[truck_mask, 'Transport'] = transport.Transport_ID
        if transport.Trailer != "":
            trucks_df.loc[truck_mask, 'Trailer'] = transport.Trailer
        
        # Save to CSV
        trucks_df.to_csv('Backend_Mobility/df_trucks.csv', index=False)
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/unassign_transport', methods=['POST'])
def unassign_transport():
    try:
        data = request.json
        transport_id = data.get('transport_id')
        
        if not transport_id:
            return jsonify({'success': False, 'error': 'Transport ID required'}), 400
        
        # Get the transport object
        transport = Transport.get_by_id(transport_id)
        if not transport:
            return jsonify({'success': False, 'error': 'Transport not found'}), 404
        
        # Check if transport has a vehicle assigned
        if transport.Vehicle == "":
            return jsonify({'success': False, 'error': 'Transport does not have a vehicle assigned'}), 400
        
        truck_license = transport.Vehicle
        
        # Update Transport object
        transport.Vehicle = ""
        transport.Driver = ""
        transport.Haulier = ""
        transport.Trailer = ""
        
        # Update Truck in DataFrame
        global trucks_df
        truck_mask = trucks_df['License_plate'] == truck_license
        if truck_mask.any():
            trucks_df.loc[truck_mask, 'Transport'] = ""
            # Truck trailer is not changed as per the function specification
            
            # Save to CSV
            trucks_df.to_csv('Backend_Mobility/df_trucks.csv', index=False)
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/transfer_truck', methods=['POST'])
def transfer_truck():
    try:
        data = request.json
        transport_id = data.get('transport_id')
        date = data.get('date')
        time = data.get('time')
        
        if not transport_id:
            return jsonify({'success': False, 'error': 'Transport ID required'}), 400
        
        if not date or not time:
            return jsonify({'success': False, 'error': 'Date and time are required'}), 400
        
        # Get the transport object
        transport = Transport.get_by_id(transport_id)
        if not transport:
            return jsonify({'success': False, 'error': 'Transport not found'}), 404
        
        # Check if transport has a vehicle assigned
        if transport.Vehicle == "":
            return jsonify({'success': False, 'error': 'No Truck assigned to transport'}), 400
        
        current_license_plate = transport.Vehicle
        
        # Update transport status to "Handled"
        transport.Status = 'Handled'
        
        # Update the truck - save current transport to Last_transport before clearing
        global trucks_df
        truck_mask = trucks_df['License_plate'] == current_license_plate
        if truck_mask.any():
            # Save current Transport to Last_transport before clearing
            current_transport = trucks_df.loc[truck_mask, 'Transport'].values[0]
            if 'Last_transport' not in trucks_df.columns:
                trucks_df['Last_transport'] = ''
            trucks_df.loc[truck_mask, 'Last_transport'] = current_transport
            trucks_df.loc[truck_mask, 'Transport'] = ""
            trucks_df.loc[truck_mask, 'Date'] = date
            trucks_df.loc[truck_mask, 'Time'] = time
        
        # Save to CSV
        trucks_df.to_csv('Backend_Mobility/df_trucks.csv', index=False)
        
        return jsonify({'success': True, 'message': f'Transport executed successfully. Truck {current_license_plate} updated to {date} {time}'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_trailer', methods=['POST'])
def update_trailer():
    global trucks_df
    try:
        data = request.json
        item_type = data.get('type')  # 'Transport' or 'Truck'
        item_id = data.get('id')
        new_trailer = data.get('trailer', '')
        
        if not item_type or not item_id:
            return jsonify({'success': False, 'error': 'Type and ID required'}), 400
        
        if item_type == 'Transport':
            # Update Transport object
            transport = Transport.get_by_id(item_id)
            if not transport:
                return jsonify({'success': False, 'error': 'Transport not found'}), 404
            
            transport.Trailer = new_trailer
            
            # If transport has a vehicle assigned, update the truck's trailer too
            if transport.Vehicle:
                truck_mask = trucks_df['License_plate'] == transport.Vehicle
                if truck_mask.any():
                    trucks_df.loc[truck_mask, 'Trailer'] = new_trailer
                    trucks_df.to_csv('Backend_Mobility/df_trucks.csv', index=False)
            
        elif item_type == 'Truck':
            # Update Truck in DataFrame
            mask = trucks_df['License_plate'] == item_id
            if not mask.any():
                return jsonify({'success': False, 'error': 'Truck not found'}), 404
            
            trucks_df.loc[mask, 'Trailer'] = new_trailer
            
            # If truck has a transport assigned, update the transport's trailer too
            truck_row = trucks_df[mask].iloc[0]
            if pd.notna(truck_row['Transport']) and truck_row['Transport'] != '':
                transport = Transport.get_by_id(truck_row['Transport'])
                if transport:
                    transport.Trailer = new_trailer
            
            # Save to CSV
            trucks_df.to_csv('Backend_Mobility/df_trucks.csv', index=False)
        else:
            return jsonify({'success': False, 'error': 'Invalid type'}), 400
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/search_trailers', methods=['POST'])
def search_trailers():
    try:
        data = request.json
        search_term = data.get('search', '').strip().upper()
        department = data.get('department', '')
        open_pool_filter = data.get('open_pool', False)
        
        if not search_term:
            return jsonify({'matches': []})
        
        # Get available trailers based on department filter and open_pool checkbox
        if open_pool_filter:
            # When checked: show all trailers with Open_pool == True (ignore department)
            available_trailers = trailers_df[
                trailers_df['Open_pool'] == True
            ]
        else:
            # When unchecked: show trailers from filtered department with Open_pool == False
            if department and department != 'ALL':
                available_trailers = trailers_df[
                    (trailers_df['Department'] == department) & 
                    (trailers_df['Open_pool'] == False)
                ]
            else:
                available_trailers = trailers_df[
                    trailers_df['Open_pool'] == False
                ]
        
        # Search for matching trailers
        matches = available_trailers[
            available_trailers['License_plate'].str.upper().str.contains(search_term, na=False)
        ]['License_plate'].tolist()
        
        return jsonify({'matches': matches})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)