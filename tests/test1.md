# test 1
June 6th, 2024
Files:
```bash
.
├── pan-europeo.qgz
└── Pan Europeo Rasters
    ├── Fire Behavior Outputs
    │   ├── flame_length_mosaic.tfw
    │   ├── flame_length_mosaic.tif
    │   ├── flame_length_mosaic.tif.aux.xml
    │   ├── flame_length_mosaic.tif.ovr
    │   ├── flame_length_mosaic.tif.ovr.aux.xml
    │   ├── flame_length_mosaic.tif.xml
    │   ├── ros_mosaic.tfw
    │   ├── ros_mosaic.tif
    │   ├── ros_mosaic.tif.aux.xml
    │   ├── ros_mosaic.tif.ovr
    │   ├── ros_mosaic.tif.ovr.aux.xml
    │   └── ros_mosaic.tif.xml
    ├── Landscape File
    │   ├── Aspect.tif
    │   ├── Biomass.tif
    │   ├── Canopy Base Height.tif
    │   ├── Canopy Bulk Density.tif
    │   ├── Canopy Cover.tif
    │   ├── Canopy Height.tif
    │   ├── Elevation.tif
    │   ├── Fuel Model.tif
    │   └── Slope.tif
    └── Risk Values
        ├── Population density.tif
        ├── Protected areas.tif
        ├── Road Europe
        │   ├── Road Europe.cpg
        │   ├── Road Europe.dbf
        │   ├── Road Europe.lyr
        │   ├── Road Europe.prj
        │   ├── Road Europe.sbn
        │   ├── Road Europe.sbx
        │   ├── Road Europe.shp
        │   └── Road Europe.shx
        └── Road Europe.zip
```

1. Roads en vector: Propuesta procesar con algoritmo de crear raster segun cercania a caminos? cual es el algo.?

2. Descriptivo, ver test1.csv:
* Marcados los 3 grupos de rasters: ojala fuesen iguales en pixel size, width, height, crs, etc.
* Pense que el CRS iba a ser en metros, EPSG:3857 ok, pero EPSG:4326 no es en metros, es en grados. 
    Aparte de la confusion, impactos:
        * (pendiente) se debe desarrollar extractor de datos matcheando cada ventana de cada raster con distintas dimensiones en vez de usar una sola ventana (si estuviesen igualados)
        * los no data vienen como np.nan

    Protected Areas -> fije a 0
    Population Density -> fije a 0
    Aspect -> ? si es entre 0 y 255, que se usa ? 0 ? 
    Slope -> ? si es entre 0 y 80, que se usa ? 0 ?
    etc...

* codigo usado en la consola de QGIS, al final de este documento

3. Falla porque se leen algunos np.nan : Son los que estan en el mar

```python3
from fire2a.raster import get_rlayer_data, get_rlayer_info
import pandas as pd
layers = iface.mapCanvas().layers()
layer_info = {} 
for lyr in layers:
    layer_info[lyr.name()] = get_rlayer_info(lyr)
df = pd.DataFrame(layer_info).T
df.to_csv('layers_info.csv')
```

