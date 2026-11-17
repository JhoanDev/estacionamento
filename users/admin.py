from django.contrib import admin
from users.models import Customer, ParkingLot, ParkingSession, Vehicle


admin.site.register([Customer, Vehicle, ParkingLot, ParkingSession])
