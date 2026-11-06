"""Our reading of the 12 specimen applicants (the official key stays with the judges)."""

EXPECTED = {
    "K01": ("review", {"gstin.status", "udyam.number"}, "GSTIN is Cancelled in the registry; Udyam number blank on the certificate"),
    "K02": ("verified", set(), "Clean; GST certificate photographed at an angle (auto-deskewed)"),
    "K03": ("verified", set(), "Clean"),
    "K04": ("fix_needed", {"gst_certificate.legible"}, "GST certificate too blurred to read"),
    "K05": ("fix_needed", {"udyam_certificate.present"}, "Udyam certificate missing"),
    "K06": ("review", {"gst_certificate.gstin"}, "GSTIN on the certificate fails the checksum; one digit differs from the registry"),
    "K07": ("review", {"gst_certificate.legal_name"}, "Legal name on the certificate differs from the registry"),
    "K08": ("verified", set(), "Clean"),
    "K09": ("verified", set(), "Clean"),
    "K10": ("verified", set(), "Clean"),
    "K11": ("fix_needed", {"address_proof.fresh"}, "Electricity bill is 257 days old"),
    "K12": ("verified", set(), "Clean"),
}
