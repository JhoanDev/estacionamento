from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import Customer, ParkingLot, ParkingSession, Vehicle


class ParkingApiTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Ana Silva", document="12345678900", phone="11999999999"
        )
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, plate="abc-1234", model="Hatch"
        )
        self.parking_lot = ParkingLot.objects.create(
            name="Centro", address="Rua Central, 1", capacity=1
        )
        self.sessions_url = reverse("parking-session-list")

    def test_customer_and_vehicle_can_be_registered(self):
        customer_response = self.client.post(
            reverse("customer-list"),
            {
                "name": "Bruno Souza",
                "document": "98765432100",
                "phone": "11888888888",
                "email": "bruno@example.com",
            },
            format="json",
        )
        self.assertEqual(customer_response.status_code, status.HTTP_201_CREATED)

        vehicle_response = self.client.post(
            reverse("vehicle-list"),
            {
                "customer": self.customer.pk,
                "plate": "xyz-9876",
                "model": "Sedan",
                "color": "Preto",
            },
            format="json",
        )
        self.assertEqual(vehicle_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(vehicle_response.data["plate"], "XYZ-9876")

    def test_check_in_tracks_occupancy_and_rejects_full_lot(self):
        response = self.client.post(
            self.sessions_url,
            {"vehicle": self.vehicle.pk, "parking_lot": self.parking_lot.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.parking_lot.refresh_from_db()
        self.assertEqual(self.parking_lot.occupied_spaces, 1)
        self.assertEqual(
            self.client.get(
                reverse("parking-lot-occupancy", args=[self.parking_lot.pk])
            ).data["available_spaces"],
            0,
        )

        another_vehicle = Vehicle.objects.create(
            customer=self.customer, plate="DEF-5678", model="SUV"
        )
        full_lot_response = self.client.post(
            self.sessions_url,
            {"vehicle": another_vehicle.pk, "parking_lot": self.parking_lot.pk},
            format="json",
        )
        self.assertEqual(full_lot_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ParkingSession.objects.count(), 1)

    def test_checkout_frees_space_and_prevents_duplicate_active_entries(self):
        response = self.client.post(
            self.sessions_url,
            {"vehicle": self.vehicle.pk, "parking_lot": self.parking_lot.pk},
            format="json",
        )
        session_id = response.data["id"]

        duplicate_response = self.client.post(
            self.sessions_url,
            {"vehicle": self.vehicle.pk, "parking_lot": self.parking_lot.pk},
            format="json",
        )
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ParkingSession.objects.count(), 1)

        checkout_response = self.client.post(
            reverse("parking-session-checkout", args=[session_id]), format="json"
        )
        self.assertEqual(checkout_response.status_code, status.HTTP_200_OK)
        self.assertFalse(checkout_response.data["is_active"])
        self.assertIsNotNone(checkout_response.data["exit_at"])

        repeated_checkout = self.client.post(
            reverse("parking-session-checkout", args=[session_id]), format="json"
        )
        self.assertEqual(repeated_checkout.status_code, status.HTTP_400_BAD_REQUEST)

        self.parking_lot.refresh_from_db()
        self.assertEqual(self.parking_lot.occupied_spaces, 0)
        self.assertEqual(self.parking_lot.available_spaces, 1)

    def test_capacity_cannot_be_reduced_below_occupancy(self):
        self.client.post(
            self.sessions_url,
            {"vehicle": self.vehicle.pk, "parking_lot": self.parking_lot.pk},
            format="json",
        )
        response = self.client.patch(
            reverse("parking-lot-detail", args=[self.parking_lot.pk]),
            {"capacity": 0},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
