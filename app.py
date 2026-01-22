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
        self.Shipment_ID = shipment_obj.Shipment_ID
        self.Transport = shipment_obj.Transport
        self.Department = shipment_obj.Department
        self.Type = stop_type

        if self.Type == 'P':
            self.Time = shipment_obj.Pickup_time
            self.Date = shipment_obj.Pickup_date
            self.Name = shipment_obj.Collection_Name
            self.City = shipment_obj.Collection_City
            self.Address = shipment_obj.Collection_Address
            self.Postal_Code = shipment_obj.Collection_Postal_Code
            self.Weight = shipment_obj.Weight
            self.Volume = shipment_obj.Volume
            self.Ldm = shipment_obj.Ldm
            self.Content = shipment_obj.Content
            self.Units = shipment_obj.Units
            self.Unit_type = shipment_obj.Unit_type
            self.Hazardous = shipment_obj.Hazardous
        elif self.Type == 'D':
            self.Time = shipment_obj.Delivery_time
            self.Date = shipment_obj.Delivery_date
            self.Name = shipment_obj.Delivery_Name
            self.City = shipment_obj.Delivery_City
            self.Address = shipment_obj.Delivery_Address
            self.Postal_Code = shipment_obj.Delivery_Postal_Code
            self.Weight = shipment_obj.Weight
            self.Volume = shipment_obj.Volume
            self.Ldm = shipment_obj.Ldm
            self.Content = shipment_obj.Content
            self.Units = shipment_obj.Units
            self.Unit_type = shipment_obj.Unit_type
            self.Hazardous = shipment_obj.Hazardous
        else:
            raise ValueError("Invalid stop type")

        stop_id = f"{self.Shipment_ID}_{self.Type}"
        Stop.registry[stop_id] = self

    @classmethod
    def get_by_id(cls, stop_id):
        return cls.registry.get(stop_id)

    def __repr__(self):
        return f"<Stop(Type='{self.Type}', Shipment_ID='{self.Shipment_ID}', Department='{self.Department}', Time='{self.Time}', Date='{self.Date}', Address='{self.Address}' '{self.Postal_Code}')>"

# Define the Shipment class
class Shipment:
    registry = {}

    def __init__(self, Shipment_ID, Transport, Department, Pickup_time, Pickup_date, Delivery_time, Delivery_date,
                 Collection_Name, Collection_City, Collection_Address, Collection_Postal_Code,
                 Delivery_Name, Delivery_City, Delivery_Address, Delivery_Postal_Code,
                 Weight, Volume, Ldm, Content, Units, Unit_type, Hazardous, Cost):
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
        self.Delivery_Name = Delivery_Name
        self.Delivery_City = Delivery_City
        self.Delivery_Address = Delivery_Address
        self.Delivery_Postal_Code = Delivery_Postal_Code
        self.Weight = Weight
        self.Volume = Volume
        self.Ldm = Ldm
        self.Content = Content
        self.Units = Units
        self.Unit_type = Unit_type
        self.Hazardous = Hazardous
        self.Cost = Cost

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

        # Collect all Stop objects from the associated Shipments
        self.Stops = []

        Transport.registry[self.Transport_ID] = self

    @classmethod
    def get_by_id(cls, Transport_ID):
        return cls.registry.get(Transport_ID)

    def __repr__(self):
        return f"<Transport(ID='{self.Transport_ID}', Department='{self.Department}', Shipments={self.Shipments}, Weight={self.Weight}, Volume={self.Volume}, Ldm={self.Ldm}, status={self.Status}, vehicle={self.Vehicle}, Haulier={self.Haulier}, Driver={self.Driver}, Trailer={self.Trailer}, Cost={self.Cost})>"

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
    for shipment_id in Shipment_IDs:
        pickup_stop_id = f"{shipment_id}_P"
        delivery_stop_id = f"{shipment_id}_D"

        pickup_stop_obj = Stop.get_by_id(pickup_stop_id)
        delivery_stop_obj = Stop.get_by_id(delivery_stop_id)

        if pickup_stop_obj:
            transport_stops.append(pickup_stop_obj)
        if delivery_stop_obj:
            transport_stops.append(delivery_stop_obj)

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

    # Update shipment objects
    for shipment_id in new_shipment_ids:
        shipment_obj = Shipment.get_by_id(shipment_id)
        if shipment_obj:
            shipment_obj.Transport = transport_obj.Transport_ID

    print(f"Added shipments {new_shipment_ids} to transport {transport_obj.Transport_ID}")
    return transport_obj

def Transport_remove(transport_id, shipment_ids):
    """
    Removes one or more shipments from a transport and updates the transport's metrics.
    """
    transport = Transport.get_by_id(transport_id)
    if not transport:
        return None

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

    if removed_count > 0:
        print(f"Successfully removed {removed_count} shipment(s) from Transport '{transport_id}'.")
        print(f"Updated Transport '{transport_id}' details: Weight={transport.Weight}, Volume={transport.Volume}, Ldm={transport.Ldm}, Cost={transport.Cost}, Stops={transport.Stops}")
    
    return transport

# Load data
shipments_df = pd.read_csv(os.path.join(BASE_DIR, 'all_shipments.csv'))
trucks_df = pd.read_csv(os.path.join(BASE_DIR, 'df_trucks.csv'))
trailers_df = pd.read_csv(os.path.join(BASE_DIR, 'df_trailers.csv'))

# Combine trucks and trailers as transports
transports_df = trucks_df.copy()

# Initialize Shipment objects
for _, row in shipments_df.iterrows():
    Shipment(
        row['Shipment_ID'], row['Transport'], row['Department'], row['Pickup_time'], row['Pickup_date'],
        row['Delivery_time'], row['Delivery_date'], row['Collection_Name'], row['Collection_City'],
        row['Collection_Address'], row['Collection_Postal_Code'], row['Delivery_Name'], row['Delivery_City'],
        row['Delivery_Address'], row['Delivery_Postal_Code'], row['Weight'], row['Volume'], row['Ldm'],
        row['Content'], row['Units'], row['Unit_type'], row['Hazardous'], row['Cost']
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shipments')
def shipments():
    # Start with the full dataframe
    filtered_df = shipments_df.copy()
    
    # Apply unassigned filter by default, unless explicitly set to 'all'
    filter_param = request.args.get('filter', 'unassigned')
    filter_unassigned = filter_param == 'unassigned'
    if filter_unassigned:
        filtered_df = filtered_df[filtered_df['Transport'].isnull() | (filtered_df['Transport'] == '')]
    
    # Apply search filters
    shipment_id = request.args.get('shipment_id', '').strip()
    if shipment_id:
        filtered_df = filtered_df[filtered_df['Shipment_ID'].str.contains(shipment_id, case=False, na=False)]
    
    # Parse postal code ranges (e.g., "2700-3500" or "2700-3500,4000-5000")
    def parse_pc_ranges(pc_string, column_name):
        if not pc_string:
            return filtered_df
        
        ranges = pc_string.split(',')
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        
        for range_str in ranges:
            range_str = range_str.strip()
            if '-' in range_str:
                parts = range_str.split('-')
                if len(parts) == 2:
                    try:
                        min_val = int(parts[0].strip())
                        max_val = int(parts[1].strip())
                        mask |= (filtered_df[column_name] >= min_val) & (filtered_df[column_name] <= max_val)
                    except ValueError:
                        pass
        
        return filtered_df[mask] if mask.any() else filtered_df
    
    collection_pc = request.args.get('collection_pc', '').strip()
    if collection_pc:
        filtered_df = parse_pc_ranges(collection_pc, 'Collection_Postal_Code')
    
    delivery_pc = request.args.get('delivery_pc', '').strip()
    if delivery_pc:
        filtered_df = parse_pc_ranges(delivery_pc, 'Delivery_Postal_Code')
    
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
    
    # Apply search filters
    transport_id = request.args.get('transport_id', '').strip()
    if transport_id:
        filtered_transports = [t for t in filtered_transports if transport_id.lower() in t.Transport_ID.lower()]
    
    # Parse postal code ranges for first and last stop
    def matches_pc_ranges(pc_value, pc_string):
        if not pc_string:
            return True
        if pc_value is None:
            return False
        
        ranges = pc_string.split(',')
        for range_str in ranges:
            range_str = range_str.strip()
            if '-' in range_str:
                parts = range_str.split('-')
                if len(parts) == 2:
                    try:
                        min_val = int(parts[0].strip())
                        max_val = int(parts[1].strip())
                        if min_val <= pc_value <= max_val:
                            return True
                    except ValueError:
                        pass
        return False
    
    collection_pc = request.args.get('collection_pc', '').strip()
    if collection_pc:
        filtered_transports = [t for t in filtered_transports 
                              if t.Stops and matches_pc_ranges(t.Stops[0].Postal_Code if t.Stops else None, collection_pc)]
    
    delivery_pc = request.args.get('delivery_pc', '').strip()
    if delivery_pc:
        filtered_transports = [t for t in filtered_transports 
                              if t.Stops and matches_pc_ranges(t.Stops[-1].Postal_Code if t.Stops else None, delivery_pc)]
    
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
        transport_data = {
            'Transport_ID': transport.Transport_ID,
            'Ldm': transport.Ldm,
            'first_stop_date': transport.Stops[0].Date if transport.Stops else '',
            'first_stop_time': transport.Stops[0].Time if transport.Stops else '',
            'last_stop_date': transport.Stops[-1].Date if transport.Stops else '',
            'last_stop_time': transport.Stops[-1].Time if transport.Stops else ''
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
        transport_id = data['transport']
        shipment_ids = data['shipments']
        transport = Transport_remove(transport_id, shipment_ids)
        if transport:
            # Update shipments_df to set Transport to None for removed shipments
            for sid in shipment_ids:
                shipments_df.loc[shipments_df['Shipment_ID'] == sid, 'Transport'] = None
            return jsonify({'message': f'Shipments removed from transport {transport_id}'})
        else:
            return jsonify({'message': 'Transport not found'}), 404
    except Exception as e:
        print("Error in remove_shipment:", e)
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/planning')
def planning():
    trucks_list = trucks_df.to_dict('records')
    transports_list = []
    
    for transport in Transport.registry.values():
        # Get first stop's location and time
        first_stop_location = ''
        first_stop_time = ''
        if transport.Stops:
            first_stop = transport.Stops[0]
            first_stop_location = f"{first_stop.City} {first_stop.Postal_Code}"
            first_stop_time = first_stop.Time
        
        # Create transport dict with additional fields
        transport_dict = {
            'Transport_ID': transport.Transport_ID,
            'Department': transport.Department,
            'Pickup_date': transport.Pickup_date,
            'Delivery_date': transport.Delivery_date,
            'Weight': transport.Weight,
            'Volume': transport.Volume,
            'Ldm': transport.Ldm,
            'Cost': transport.Cost,
            'Status': transport.Status,
            'Vehicle': transport.Vehicle,
            'Haulier': transport.Haulier,
            'Driver': transport.Driver,
            'first_stop_location': first_stop_location,
            'first_stop_time': first_stop_time
        }
        transports_list.append(transport_dict)
    
    return render_template('planning.html', trucks=trucks_list, transports=transports_list)

@app.route('/planning/stops/<type>/<id>')
def planning_stops(type, id):
    if type == 'transport':
        transport = Transport.get_by_id(id)
        if transport and transport.Stops:
            stops_data = []
            for stop in transport.Stops:
                stops_data.append({
                    'Type': stop.Type,
                    'Name': stop.Name,
                    'Address': stop.Address,
                    'City': stop.City,
                    'Postal_Code': stop.Postal_Code,
                    'Date': stop.Date,
                    'Time': stop.Time,
                    'Weight': stop.Weight,
                    'Volume': stop.Volume,
                    'Ldm': stop.Ldm
                })
            return jsonify({'stops': stops_data})
    return jsonify({'stops': []})

if __name__ == '__main__':
    app.run(debug=True)