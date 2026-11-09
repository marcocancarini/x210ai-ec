/*
 * X210AI: ACPI 4.0 fan and temperature on top of the EC fan patch.
 *
 * DRAFT, never loaded on the board. See docs/4-ventola-acpi.md, section 4.7.
 *
 * Needs the EC patch of docs/8-ventole-firmware.md 8.8 (tools/emulator/host_ctl.py):
 *   0x74-0x75  tachometer count, fan 1, low byte first
 *   0xC9       requested duty, 0-152
 *   0xCA       timer: 0 off, 1-254 tenths of a second, 255 no expiry
 * On the factory EC the fan methods write two unused bytes and change nothing, and the
 * speed reads 0: the table can be tested before the flash, see 4.7.
 *
 * Build:  iasl x210ai-fan.asl      ->  x210ai-fan.aml
 */
DefinitionBlock ("", "SSDT", 2, "X210AI", "ECFAN", 0x00000001)
{
    External (\_SB.PC00.LPCB.H_EC, DeviceObj)

    Scope (\_SB.PC00.LPCB.H_EC)
    {
        /* Offsets 0x40-0xCF of the EC space. The DSDT ECF2 field names none of these */
        OperationRegion (XFRG, EmbeddedControl, 0x40, 0x90)
        Field (XFRG, ByteAcc, Lock, Preserve)
        {
            Offset (0x06),
            XDT0,   8,      /* 0x46 current duty, fan 1, 0-152 */
            Offset (0x30),
            XTMP,   8,      /* 0x70 CPU temperature read by the EC, C */
            Offset (0x34),
            XTC0,   16,     /* 0x74 tachometer count, fan 1 */
            Offset (0x89),
            XHDU,   8,      /* 0xC9 requested duty */
            XHTM,   8       /* 0xCA timer */
        }
    }

    Device (\_SB.XFAN)
    {
        Name (_HID, EisaId ("PNP0C0B"))
        Name (_UID, 0x10)   /* \_TZ.FAN0-FAN4 use 0-4 */
        Name (_STR, Unicode ("X210AI EC fan"))

        /* Revision, fine grain control, 1 % steps, no low speed notification */
        Name (_FIF, Package () { Zero, One, One, Zero })

        /*
         * Control %, trip point, speed rpm, noise, power. The speeds are guesses from the
         * simulator model (5000 rpm at 100 %): replace them with measured values.
         */
        Name (_FPS, Package ()
        {
            Zero,
            Package () {   0, 0xFFFFFFFF,    0, 0xFFFFFFFF, 0xFFFFFFFF },
            Package () {  25, 0xFFFFFFFF, 1250, 0xFFFFFFFF, 0xFFFFFFFF },
            Package () {  50, 0xFFFFFFFF, 2500, 0xFFFFFFFF, 0xFFFFFFFF },
            Package () {  75, 0xFFFFFFFF, 3750, 0xFFFFFFFF, 0xFFFFFFFF },
            Package () { 100, 0xFFFFFFFF, 5000, 0xFFFFFFFF, 0xFFFFFFFF }
        })

        /* Request a duty in %, with no expiry. At 85 C or above the EC uses the higher of
         * request and curve; sleep clears the request */
        Method (_FSL, 1, Serialized)
        {
            Local0 = Arg0
            If (Local0 > 100)
            {
                Local0 = 100
            }
            \_SB.PC00.LPCB.H_EC.XHDU = ((Local0 * 152) / 100)
            \_SB.PC00.LPCB.H_EC.XHTM = 0xFF
        }

        /* Revision, current control in %, speed in rpm (0 if stopped or no tachometer) */
        Name (FSTP, Package (0x03) { Zero, Zero, Zero })
        Method (_FST, 0, Serialized)
        {
            FSTP [One] = ((\_SB.PC00.LPCB.H_EC.XDT0 * 100) / 152)
            Local0 = \_SB.PC00.LPCB.H_EC.XTC0
            If (Local0 == Zero)
            {
                FSTP [0x02] = Zero
            }
            Else
            {
                /* 60 * (9.2 MHz / 128) / 2 pulses per turn, datasheet IT5570 7.12.3.2 */
                FSTP [0x02] = (2156250 / Local0)
            }
            Return (FSTP)
        }

        /* Not standard: give the fan back to the EC curve, e.g. with acpi_call */
        Method (XAUT, 0, Serialized)
        {
            \_SB.PC00.LPCB.H_EC.XHTM = Zero
        }
    }

    /*
     * Real CPU temperature for Linux, instead of the 27.85 C constant of \_TZ.TZ00.
     * No trip points on purpose: on the factory EC a PECI error reads as 110 C (L3 in
     * docs 8.2), and a _CRT would shut the machine down. Add trips only with that fix.
     */
    ThermalZone (\_TZ.XTZ0)
    {
        Method (_TMP, 0, Serialized)
        {
            Return (((\_SB.PC00.LPCB.H_EC.XTMP * 10) + 2732))
        }
        Name (_TZP, 50)     /* poll every 5 s */
        Name (_STR, Unicode ("X210AI EC CPU temperature"))
    }
}
