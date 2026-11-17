from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import serializers

from users.models import (
    Customer,
    ParkingLot,
    ParkingSession,
    UserProfileExample,
    Vehicle,
)


class UserProfileExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfileExample
        fields = ["id", "address", "phone_number", "birth_date", "user"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "document", "phone", "email", "created_at"]
        read_only_fields = ["id", "created_at"]


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ["id", "customer", "plate", "model", "color"]
        read_only_fields = ["id"]

    def validate_plate(self, value):
        return value.strip().upper()


class ParkingLotSerializer(serializers.ModelSerializer):
    available_spaces = serializers.IntegerField(read_only=True)

    class Meta:
        model = ParkingLot
        fields = ["id", "name", "address", "capacity", "occupied_spaces", "available_spaces"]
        read_only_fields = ["id", "occupied_spaces", "available_spaces"]

    def validate_capacity(self, value):
        if self.instance and value < self.instance.occupied_spaces:
            raise serializers.ValidationError(
                "A capacidade não pode ser menor que a quantidade de vagas ocupadas."
            )
        return value


class ParkingSessionSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True)
    parking_lot_name = serializers.CharField(source="parking_lot.name", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ParkingSession
        fields = [
            "id",
            "vehicle",
            "vehicle_plate",
            "parking_lot",
            "parking_lot_name",
            "entry_at",
            "exit_at",
            "is_active",
        ]
        read_only_fields = ["id", "entry_at", "exit_at", "is_active"]

    def create(self, validated_data):
        vehicle = validated_data["vehicle"]
        parking_lot = validated_data["parking_lot"]

        with transaction.atomic():
            if ParkingSession.objects.filter(
                vehicle=vehicle, exit_at__isnull=True
            ).exists():
                raise serializers.ValidationError(
                    {"vehicle": "Este veículo já possui uma entrada em aberto."}
                )

            updated = ParkingLot.objects.filter(
                pk=parking_lot.pk,
                occupied_spaces__lt=F("capacity"),
            ).update(occupied_spaces=F("occupied_spaces") + 1)
            if not updated:
                raise serializers.ValidationError(
                    {"parking_lot": "Não há vagas disponíveis neste estacionamento."}
                )

            try:
                with transaction.atomic():
                    return ParkingSession.objects.create(**validated_data)
            except IntegrityError as error:
                raise serializers.ValidationError(
                    {"vehicle": "Este veículo já possui uma entrada em aberto."}
                ) from error
