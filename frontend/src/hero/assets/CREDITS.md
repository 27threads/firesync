# Assets da abertura (globo)

- `earth-surface.jpg` (2048 × 1024) e `earth-fast.jpg` (512 × 256): camada `BlueMarble_ShadedRelief_Bathymetry` do NASA GIBS, pedida como uma imagem equirretangular no WMS do GIBS (`https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi`). Imagery courtesy of NASA EOSDIS GIBS.

## Modelos das espaçonaves

- `aqua.glb` — Aqua (B): https://github.com/nasa/NASA-3D-Resources/tree/master/3D%20Models/Aqua%20(B) — NASA 3D Resources, public domain / free and without copyright per repository README. Aqua carries MODIS, the MODIS host used in the harmonized record.
- `suomi-npp.glb` — Suomi NPP: https://github.com/nasa/NASA-3D-Resources/tree/master/3D%20Models/Suomi%20National%20Polar-orbiting%20Partnership%20(Suomi%20NPP) — NASA/Brian E. Kumanchik; NASA/Christian A. Lopez. NASA 3D Resources, public domain / free and without copyright per repository README. Suomi NPP carries VIIRS; the scene labels it S-NPP → NOAA-20, the VIIRS hosts used in the harmonized record, and the model does not depict NOAA-20.
- Both files are the NASA originals with the Draco mesh compression decoded (`@gltf-transform`), so Three.js loads them without a Draco decoder. Geometry, materials and textures are unchanged.
- Usage guidelines: https://www.nasa.gov/nasa-brand-center/images-and-media/ . No NASA endorsement is implied. Scene orbital paths, relative sizes and animation timing are illustrative, not physical tracking data.
