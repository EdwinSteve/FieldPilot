# Common bean (Phaseolus vulgaris): what is sourced, what is missing

Research done on 2026-11-02 for a second crop after D077. The conclusion is
in D078: the bean waits for a days-based phenology model instead of entering
the catalogue with converted stage thresholds.

## Verified against the primary source

| Value | Data | Source |
|---|---|---|
| Kc ini, Kc mid, Kc end | 0.4, 1.15, 0.35 ("Beans, dry and Pulses"). Footnote 2: Kc mid 1.20 for dry beans grown on 1.5-2 m stalks | FAO-56, Table 12 |
| Stage lengths, days (initial, development, mid, late) | 20/30/40/20, 110 days (May/June, continental climates); 15/25/35/20, 95 days (June, Pakistan, California); 25/25/30/20, 100 days (June, Idaho) | FAO-56, Table 11 |
| Maximum effective root depth | 0.6-0.9 m; depletion fraction p = 0.45 | FAO-56, Table 22 |
| Development scale | V0 germination, V1 emergence, V2 primary leaves, V3 first trifoliate, V4 third trifoliate, R5 pre-flowering, R6 flowering, R7 pod formation, R8 pod filling, R9 maturity | CIAT (1986). The reference and the scale names are confirmed; its days per stage were not read (see below) |

## Not verified

- **The GDD base temperature.** Studies disagree. An Acta Horticulturae
  study in a Mediterranean environment found the standard 10 °C formula
  predicted flowering and first-pod ripening better than calendar days.
  Other work fits better with bases of 4.5 to 8 °C, and a Quebec snap-bean
  study found 0 °C or 6.7 °C depending on the cultivar.
- **Degree-days per stage.** No published table was found. The only total
  is UNL CropWatch (2009): 1,550-1,700 GDD (°F) to maturity for great
  northern beans in Nebraska. That is one market class, in another climate,
  with no intermediate stages. A 1,100-1,300 GDD figure in Wikipedia has no
  traceable source.
- **CIAT's days per stage.** Both copies of the PDF on the CIAT library
  server failed to load (connection reset). The CGSpace record exists.

## Why the bean was not added

FieldPilot's phenology counts degree-days from sowing (D017, D031). The
reliable bean data for the tropics (FAO-56 Table 11, CIAT) is in days after
sowing. Entering it would mean converting days to degree-days with an
assumed temperature: a project convention presented as a crop parameter.
That conversion would set each stage's moisture target and Kc, which steer
irrigation.

## Recommended path

1. A days-based phenology model. A crop's YAML declares whether its stages
   are counted in degree-days or in days after sowing, and the engine follows
   it. This is the first step of option B in D077, and it serves many
   tropical crops.
2. The bean, on that model, with FAO-56 Tables 11, 12 and 22. Use CIAT's days
   per stage where they fit Colombian conditions, once the PDF is read.
3. A review by an agronomist before `reviewed_by_agronomist` becomes true,
   as for maize.

## Sources

- FAO-56, chapter 6 (Tables 11 and 12): http://www.fao.org/4/x0490e/x0490e0b.htm
- FAO-56, chapter 8 (Table 22): http://www.fao.org/4/x0490e/x0490e0e.htm
- Fernández de Córdova, F., Gepts, P. & López, M. (1986). Etapas de
  desarrollo de la planta de fríjol común (Phaseolus vulgaris L.). CIAT, Cali.
  - Record: https://cgspace.cgiar.org/items/96cbac5a-0e27-4629-99a0-2099860dae35
  - PDF (did not load on 2026-11-02): http://ciat-library.ciat.cgiar.org/ciat_digital/ciat/28093.pdf
- UNL CropWatch (2009), 8-21-09 Dry Beans: https://cropwatch.unl.edu/8-21-09-dry-beans/
- Validity of thermal unit summations for purposes of prediction in Phaseolus
  vulgaris L. cropped in Mediterranean environment, Acta Horticulturae 229:
  https://www.actahort.org/books/229/229_35.htm
