from datetime import datetime, timedelta


class User:
    def __init__(self, user_id, name, email):
        self.user_id = user_id
        self.name = name
        self.email = email

    def view_scooter_availability(self, system):
        return system.search_available_scooters()

    def view_station_locations(self, system):
        return [(station.station_id, station.name, station.location) for station in system.stations]


class GuestUser(User):
    def register(self, system, password):
        return system.register_user(self.name, self.email, password)


class RegisteredUser(User):
    def __init__(self, user_id, name, email, password):
        super().__init__(user_id, name, email)
        self.password = password
        self.rental_history = []

    def login(self, email, password):
        return self.email == email and self.password == password

    def reserve_scooter(self, system, scooter_id):
        return system.create_reservation(self.user_id, scooter_id)

    def rent_scooter(self, system, scooter_id):
        return system.create_rental(self.user_id, scooter_id)

    def return_scooter(self, system, rental_id, station_id, duration_minutes):
        return system.return_scooter(rental_id, station_id, duration_minutes)

    def view_rental_history(self):
        return self.rental_history

    def report_faulty_scooter(self, system, scooter_id, issue_description):
        return system.report_fault(scooter_id, issue_description)


class Scooter:
    def __init__(self, scooter_id, battery_level, scooter_type, location):
        self.scooter_id = scooter_id
        self.battery_level = battery_level
        self.status = "available"
        self.scooter_type = scooter_type
        self.location = location
        self.current_station = None

    def reserve(self):
        if self.status != "available":
            raise ValueError("Scooter is not available for reservation.")
        self.status = "reserved"

    def unlock(self):
        if self.status not in ["available", "reserved"]:
            raise ValueError("Scooter cannot be unlocked.")
        self.status = "in_use"

    def mark_in_use(self):
        if self.status not in ["available", "reserved"]:
            raise ValueError("Scooter cannot be marked as in use.")
        self.status = "in_use"

    def return_to_station(self, station):
        self.current_station = station
        self.location = station.location
        self.status = "available"

    def mark_under_maintenance(self):
        self.status = "under_maintenance"

    def mark_available(self):
        self.status = "available"


class Station:
    def __init__(self, station_id, name, location, capacity):
        self.station_id = station_id
        self.name = name
        self.location = location
        self.capacity = capacity
        self.scooters = []

    def add_scooter(self, scooter):
        if not self.has_capacity():
            raise ValueError("Station capacity is full.")
        if scooter not in self.scooters:
            self.scooters.append(scooter)
        scooter.current_station = self
        scooter.location = self.location

    def remove_scooter(self, scooter):
        if scooter in self.scooters:
            self.scooters.remove(scooter)
            scooter.current_station = None
            scooter.location = "GPS / In transit"

    def get_available_scooters(self):
        return [scooter for scooter in self.scooters if scooter.status == "available"]

    def has_capacity(self):
        return len(self.scooters) < self.capacity


class Rental:
    RATE_PER_MINUTE = {
        "standard": 1.00,
        "premium": 2.00
    }

    def __init__(self, rental_id, user, scooter):
        self.rental_id = rental_id
        self.user = user
        self.scooter = scooter
        self.start_time = None
        self.end_time = None
        self.total_cost = 0.0
        self.status = "created"

    def start_rental(self):
        self.start_time = datetime.now()
        self.status = "active"
        self.scooter.mark_in_use()

    def end_rental(self, duration_minutes):
        if self.status != "active":
            raise ValueError("Only active rentals can be ended.")
        self.end_time = self.start_time + timedelta(minutes=duration_minutes)
        self.total_cost = self.calculate_cost(duration_minutes)
        self.status = "completed"
        return self.total_cost

    def calculate_cost(self, duration_minutes):
        rate = self.RATE_PER_MINUTE.get(self.scooter.scooter_type.lower(), 1.00)
        return duration_minutes * rate


class Reservation:
    def __init__(self, reservation_id, user, scooter):
        self.reservation_id = reservation_id
        self.user = user
        self.scooter = scooter
        self.reservation_time = datetime.now()
        self.status = "created"

    def confirm_reservation(self):
        self.scooter.reserve()
        self.status = "confirmed"

    def cancel_reservation(self):
        if self.status == "confirmed":
            self.scooter.mark_available()
        self.status = "cancelled"

    def expire_reservation(self):
        if self.status == "confirmed":
            self.scooter.mark_available()
        self.status = "expired"

    def convert_to_rental(self):
        self.status = "converted_to_rental"


class MaintenanceRecord:
    def __init__(self, record_id, scooter, issue_description):
        self.record_id = record_id
        self.scooter = scooter
        self.issue_description = issue_description
        self.reported_date = datetime.now()
        self.repair_date = None
        self.status = "open"

    def create_record(self):
        self.scooter.mark_under_maintenance()
        self.status = "open"

    def mark_repaired(self):
        self.repair_date = datetime.now()
        self.status = "repaired"
        self.scooter.mark_available()


class ScooterRentalSystem:
    def __init__(self):
        self.users = []
        self.scooters = []
        self.stations = []
        self.rentals = []
        self.reservations = []
        self.maintenance_records = []
        self.next_user_id = 1
        self.next_rental_id = 1
        self.next_reservation_id = 1
        self.next_maintenance_id = 1

    def register_user(self, name, email, password):
        user = RegisteredUser(self.next_user_id, name, email, password)
        self.users.append(user)
        self.next_user_id += 1
        return user

    def add_station(self, station):
        self.stations.append(station)

    def add_scooter(self, scooter, station_id):
        station = self.find_station(station_id)
        if station is None:
            raise ValueError("Station not found.")
        station.add_scooter(scooter)
        self.scooters.append(scooter)

    def search_available_scooters(self):
        return [scooter for scooter in self.scooters if scooter.status == "available"]

    def create_reservation(self, user_id, scooter_id):
        user = self.find_user(user_id)
        scooter = self.find_scooter(scooter_id)

        if user is None or scooter is None:
            raise ValueError("User or scooter not found.")
        if scooter.status != "available":
            raise ValueError("Scooter is not available for reservation.")

        reservation = Reservation(self.next_reservation_id, user, scooter)
        reservation.confirm_reservation()

        self.reservations.append(reservation)
        self.next_reservation_id += 1
        return reservation

    def create_rental(self, user_id, scooter_id):
        user = self.find_user(user_id)
        scooter = self.find_scooter(scooter_id)

        if user is None or scooter is None:
            raise ValueError("User or scooter not found.")
        if scooter.status == "under_maintenance":
            raise ValueError("Scooter is under maintenance and cannot be rented.")
        if scooter.status == "in_use":
            raise ValueError("Scooter is already in use.")

        active_reservation = self.find_active_reservation_for_scooter(scooter_id)

        if scooter.status == "reserved":
            if active_reservation is None or active_reservation.user.user_id != user_id:
                raise ValueError("Scooter is reserved by another user.")
            active_reservation.convert_to_rental()

        if scooter.current_station is not None:
            scooter.current_station.remove_scooter(scooter)

        rental = Rental(self.next_rental_id, user, scooter)
        rental.start_rental()

        self.rentals.append(rental)
        user.rental_history.append(rental)
        self.next_rental_id += 1
        return rental

    def return_scooter(self, rental_id, station_id, duration_minutes):
        rental = self.find_rental(rental_id)
        station = self.find_station(station_id)

        if rental is None or station is None:
            raise ValueError("Rental or station not found.")
        if not station.has_capacity():
            raise ValueError("Cannot return scooter because the station is full.")

        total_cost = rental.end_rental(duration_minutes)
        station.add_scooter(rental.scooter)
        rental.scooter.return_to_station(station)
        return total_cost

    def report_fault(self, scooter_id, issue_description):
        scooter = self.find_scooter(scooter_id)
        if scooter is None:
            raise ValueError("Scooter not found.")

        record = MaintenanceRecord(self.next_maintenance_id, scooter, issue_description)
        record.create_record()

        self.maintenance_records.append(record)
        self.next_maintenance_id += 1
        return record

    def repair_scooter(self, record_id):
        record = self.find_maintenance_record(record_id)
        if record is None:
            raise ValueError("Maintenance record not found.")
        record.mark_repaired()
        return record

    def find_user(self, user_id):
        for user in self.users:
            if user.user_id == user_id:
                return user
        return None

    def find_scooter(self, scooter_id):
        for scooter in self.scooters:
            if scooter.scooter_id == scooter_id:
                return scooter
        return None

    def find_station(self, station_id):
        for station in self.stations:
            if station.station_id == station_id:
                return station
        return None

    def find_rental(self, rental_id):
        for rental in self.rentals:
            if rental.rental_id == rental_id:
                return rental
        return None

    def find_maintenance_record(self, record_id):
        for record in self.maintenance_records:
            if record.record_id == record_id:
                return record
        return None

    def find_active_reservation_for_scooter(self, scooter_id):
        for reservation in self.reservations:
            if reservation.scooter.scooter_id == scooter_id and reservation.status == "confirmed":
                return reservation
        return None


if __name__ == "__main__":
    system = ScooterRentalSystem()

    station1 = Station(1, "Main Campus Station", "Campus Gate A", 3)
    station2 = Station(2, "Library Station", "University Library", 3)

    system.add_station(station1)
    system.add_station(station2)

    scooter1 = Scooter(101, 90, "standard", station1.location)
    scooter2 = Scooter(102, 80, "premium", station1.location)
    scooter3 = Scooter(103, 60, "standard", station2.location)

    system.add_scooter(scooter1, 1)
    system.add_scooter(scooter2, 1)
    system.add_scooter(scooter3, 2)

    user1 = system.register_user("Ahmed Khan", "ahmed@example.com", "pass123")
    user2 = system.register_user("Sara Ali", "sara@example.com", "pass456")

    print("Available scooters before rental:")
    for scooter in system.search_available_scooters():
        print(f"Scooter {scooter.scooter_id} - {scooter.scooter_type} - {scooter.status}")

    reservation = user1.reserve_scooter(system, 101)
    print(f"\nReservation {reservation.reservation_id} created for scooter {reservation.scooter.scooter_id}")

    try:
        user2.rent_scooter(system, 101)
    except ValueError as error:
        print(f"\nDouble rental prevented: {error}")

    rental = user1.rent_scooter(system, 101)
    print(f"\nRental {rental.rental_id} started for scooter {rental.scooter.scooter_id}")

    cost = user1.return_scooter(system, rental.rental_id, 2, duration_minutes=15)
    print(f"Rental completed. Total cost: AED {cost:.2f}")

    fault_record = user1.report_faulty_scooter(system, 102, "Brake issue reported")
    print(f"\nFault reported for scooter {fault_record.scooter.scooter_id}")

    try:
        user2.rent_scooter(system, 102)
    except ValueError as error:
        print(f"Maintenance rental blocked: {error}")

    repaired_record = system.repair_scooter(fault_record.record_id)
    print(f"Scooter {repaired_record.scooter.scooter_id} repaired and marked as {repaired_record.scooter.status}")

    print("\nUser rental history:")
    for rental in user1.view_rental_history():
        print(f"Rental {rental.rental_id}: Scooter {rental.scooter.scooter_id}, Cost AED {rental.total_cost:.2f}, Status {rental.status}")