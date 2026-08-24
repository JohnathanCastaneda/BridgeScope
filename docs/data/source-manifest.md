# FHWA 2025 California NBI Source Manifest 

## Dataset identity 

- Provider: Federal Highway Administration 
- Dataset: National Bridge Inventory highway-bridge records 
- State: California - State code: 06 - Inventory year: 2025 
- Source specification: Legacy NBI export format 
- Source format: Comma-delimited text 
- Source file name: CA25.txt 

## Source locations 

- Source page: https://www.fhwa.dot.gov/bridge/nbi/ascii2025.cfm 
- Direct file URL: https://www.fhwa.dot.gov/bridge/nbi/2025/delimited/CA25.txt 

## Retrieved file 

- Retrieved at UTC: 2026-08-24T04:41:55Z
- File size in bytes: 10,710,461
- SHA-256: 6f9cf692cd82ff9ad57579e3f746bdfc55126882933b3d0e2815dabe6cb465f5
- Total physical lines: 25,976
- Header rows: 1 
- Local data rows: 25,975
- Publisher-reported bridge records: 25,975 

## File format 

- Delimiter: Comma 
- Text qualifier: Single quote 
- Header present: Yes 
- Header column count: TBD
- Character encoding: TBD

## Storage policy 

The full raw file is stored locally at `data/raw/CA25.txt`. 

The file is excluded from Git because it can be downloaded again from the documented source. A representative sample fixture will be created and committed separately. The raw file must remain unchanged after its checksum is calculated. Any normalization or correction will occur in importer output rather than by editing the source file. 

## Important interpretation notes 
- The inventory year does not necessarily match the traffic measurement year. 
- The inventory year does not necessarily match the inspection year. 
- Average Daily Traffic is an estimate and is not live traffic. 
- Condition classifications must not be presented as proof that a bridge is safe or unsafe. 
- A future file with the same inventory year but a different SHA-256 checksum must be treated as a different source revision.