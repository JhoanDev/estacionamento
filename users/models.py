from django.db import models
from django.contrib.auth.models import User
from django.db.models import F, Q

# Create your models here.

class UserProfileExample(models.Model):

    phone_number = models.CharField(max_length=12)
    address = models.CharField(max_length=150)
    birth_date = models.DateField()
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"


class Customer(models.Model):
    name = models.CharField(max_length=150)
    document = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="vehicles"
    )
    plate = models.CharField(max_length=10, unique=True)
    model = models.CharField(max_length=100)
    color = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        self.plate = self.plate.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.plate


class ParkingLot(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField()
    occupied_spaces = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(capacity__gt=0), name="parking_lot_capacity_positive"
            ),
            models.CheckConstraint(
                check=Q(occupied_spaces__lte=F("capacity")),
                name="parking_lot_occupancy_within_capacity",
            ),
        ]

    @property
    def available_spaces(self):
        return self.capacity - self.occupied_spaces

    def __str__(self):
        return self.name


class ParkingSession(models.Model):
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name="parking_sessions"
    )
    parking_lot = models.ForeignKey(
        ParkingLot, on_delete=models.PROTECT, related_name="parking_sessions"
    )
    entry_at = models.DateTimeField(auto_now_add=True)
    exit_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-entry_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(exit_at__isnull=True),
                name="one_active_parking_session_per_vehicle",
            )
        ]

    @property
    def is_active(self):
        return self.exit_at is None

    def __str__(self):
        return f"{self.vehicle.plate} - {self.entry_at}"
