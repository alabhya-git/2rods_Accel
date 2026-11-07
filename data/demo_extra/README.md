# Demo documents (ours, not the official pack)

The official specimen pack has no rented shop. `K02R` is K02's clinic in a rented unit, made by
`api/scripts/make_rented_demo.py`:

- `K02R_address_proof.png`: K02's electricity bill, in the landlord's name (Sunita Banerjee).
- `K02R_rent_agreement.png`: a rent agreement naming the landlord, the tenant (K02's proprietor)
  and the same address.

K02R's GST certificate and signatory ID are K02's own. The judge console's 12-applicant KYC run
does not include K02R; its expected outcomes are in `api/tests/test_painpoints.py`.
