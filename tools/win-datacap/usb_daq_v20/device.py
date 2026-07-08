"""Device discovery, CardID registry, and session management."""

from __future__ import annotations

from dataclasses import dataclass

import usb.core
import usb.backend.libusb1
import usb.util
import libusb_package

from ._card_id import read_card_id
from .constants import INTERFACE, MAX_DEVICES, PID, VID
from .errors import DaqError, ErrorCode


@dataclass(frozen=True)
class DeviceInfo:
    card_id: int
    bus: int
    address: int


@dataclass
class DeviceSession:
    dev: usb.core.Device
    card_id: int
    bus: int
    address: int


def _backend():
    return usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)


def _find_daq_devices() -> list[usb.core.Device]:
    devices = list(
        usb.core.find(
            find_all=True,
            idVendor=VID,
            idProduct=PID,
            backend=_backend(),
        )
        or []
    )
    if len(devices) > MAX_DEVICES:
        devices = devices[:MAX_DEVICES]
    return devices


def _prepare_device(dev: usb.core.Device) -> None:
    try:
        if dev.is_kernel_driver_active(INTERFACE):
            dev.detach_kernel_driver(INTERFACE)
    except (NotImplementedError, usb.core.USBError):
        pass

    try:
        dev.set_configuration()
    except usb.core.USBError:
        pass

    try:
        usb.util.claim_interface(dev, INTERFACE)
    except usb.core.USBError as e:
        raise DaqError(
            ErrorCode.CLAIM_FAILED,
            "claim_interface 失败，接口可能被占用或驱动不正确",
            stage="claim",
            usb_errno=getattr(e, "errno", None),
            bus=dev.bus,
            address=dev.address,
        ) from e


def _release_device(dev: usb.core.Device) -> None:
    try:
        usb.util.release_interface(dev, INTERFACE)
        usb.util.dispose_resources(dev)
    except usb.core.USBError:
        pass


def _open_single_device(dev: usb.core.Device) -> DeviceSession:
    _prepare_device(dev)
    card_id = read_card_id(dev)
    return DeviceSession(
        dev=dev,
        card_id=card_id,
        bus=dev.bus,
        address=dev.address,
    )


class DeviceManager:
    """Singleton manager for opened USB-DAQ devices indexed by CardID."""

    def __init__(self) -> None:
        self._opened = False
        self._registry: dict[int, DeviceSession] = {}

    @property
    def is_open(self) -> bool:
        return self._opened

    def resolve(self, card_id: int) -> DeviceSession:
        if not self._opened:
            raise DaqError(
                ErrorCode.NOT_OPENED,
                "设备未打开，请先调用 open_all()",
                stage="lookup",
            )
        session = self._registry.get(card_id)
        if session is None:
            known = ", ".join(f"0x{cid:08X}" for cid in self._registry)
            raise DaqError(
                ErrorCode.DEVICE_NOT_FOUND,
                f"未找到 CardID=0x{card_id:08X}，当前已打开: [{known}]",
                stage="lookup",
                card_id=card_id,
            )
        return session

    def open_all(self) -> list[DeviceInfo]:
        """Open all DAQ devices (OpenUsbV20_V2 semantics)."""
        if self._opened:
            self.close_all()

        raw_devices = _find_daq_devices()
        if not raw_devices:
            raise DaqError(
                ErrorCode.NO_DAQ_DEVICE,
                f"未找到 USB-DAQ 设备 (VID=0x{VID:04X}, PID=0x{PID:04X})",
                stage="enumerate",
            )

        sessions: list[DeviceSession] = []
        opened_devs: list[usb.core.Device] = []

        for dev in raw_devices:
            try:
                session = _open_single_device(dev)
            except DaqError:
                for opened in opened_devs:
                    _release_device(opened)
                raise
            except usb.core.USBError as e:
                for opened in opened_devs:
                    _release_device(opened)
                raise DaqError(
                    ErrorCode.OPEN_FAILED,
                    "打开 USB 设备失败",
                    stage="open",
                    usb_errno=getattr(e, "errno", None),
                    bus=dev.bus,
                    address=dev.address,
                ) from e

            opened_devs.append(dev)
            sessions.append(session)

        # TODO: 理论上 CardID 不应重复；若硬件出现重复需扩展为 (card_id, bus, address) 复合键
        card_id_map: dict[int, list[DeviceSession]] = {}
        for session in sessions:
            card_id_map.setdefault(session.card_id, []).append(session)

        duplicates = {cid: group for cid, group in card_id_map.items() if len(group) > 1}
        if duplicates:
            for opened in opened_devs:
                _release_device(opened)
            details = []
            for cid, group in duplicates.items():
                locs = ", ".join(f"bus={s.bus} addr={s.address}" for s in group)
                details.append(f"CardID=0x{cid:08X}: {locs}")
            raise DaqError(
                ErrorCode.DUPLICATE_CARD_ID,
                "发现重复 CardID: " + "; ".join(details),
                stage="register",
            )

        self._registry = {s.card_id: s for s in sessions}
        self._opened = True
        return [
            DeviceInfo(card_id=s.card_id, bus=s.bus, address=s.address)
            for s in sessions
        ]

    def close_all(self) -> None:
        if not self._opened:
            return
        for session in self._registry.values():
            _release_device(session.dev)
        self._registry.clear()
        self._opened = False

    def list_devices(self) -> list[DeviceInfo]:
        if self._opened:
            return [
                DeviceInfo(card_id=s.card_id, bus=s.bus, address=s.address)
                for s in self._registry.values()
            ]
        return probe_devices()

    def list_card_ids(self) -> list[int]:
        return [info.card_id for info in self.list_devices()]

    def get_device_count(self) -> int:
        if not self._opened:
            return 0
        return len(self._registry)

    def get_card_id(self, card_id: int) -> int:
        session = self.resolve(card_id)
        return session.card_id

    def reset_device(self, card_id: int) -> None:
        session = self.resolve(card_id)
        try:
            session.dev.reset()
        except usb.core.USBError as e:
            raise DaqError(
                ErrorCode.RESET_FAILED,
                "USB 设备 reset 失败",
                stage="reset",
                card_id=card_id,
                usb_errno=getattr(e, "errno", None),
                bus=session.bus,
                address=session.address,
            ) from e
        _release_device(session.dev)
        del self._registry[card_id]
        if not self._registry:
            self._opened = False


def probe_devices() -> list[DeviceInfo]:
    """Briefly open each device to read CardID without keeping sessions."""
    raw_devices = _find_daq_devices()
    if not raw_devices:
        return []

    results: list[DeviceInfo] = []
    seen_ids: dict[int, list[tuple[int, int]]] = {}

    for dev in raw_devices:
        try:
            _prepare_device(dev)
            card_id = read_card_id(dev)
            seen_ids.setdefault(card_id, []).append((dev.bus, dev.address))
            results.append(DeviceInfo(card_id=card_id, bus=dev.bus, address=dev.address))
        except DaqError:
            raise
        finally:
            _release_device(dev)

    # TODO: 理论上 CardID 不应重复；若硬件出现重复需扩展为复合键
    duplicates = {cid: locs for cid, locs in seen_ids.items() if len(locs) > 1}
    if duplicates:
        details = []
        for cid, locs in duplicates.items():
            loc_str = ", ".join(f"bus={b} addr={a}" for b, a in locs)
            details.append(f"CardID=0x{cid:08X}: {loc_str}")
        raise DaqError(
            ErrorCode.DUPLICATE_CARD_ID,
            "发现重复 CardID: " + "; ".join(details),
            stage="probe",
        )

    return results


_manager = DeviceManager()


def get_manager() -> DeviceManager:
    return _manager
