# Open Questions

## Physics

1. Which gases have useful HITRAN lines between 60 and 400 GHz?
2. Are VOCs realistic in this band, or should the first experiment focus on CO, O3, SO2, or NO2?
3. Which PM attenuation model is defensible for 60 to 400 GHz?
4. How much does elevation improve sensing through longer slant path before communication quality collapses?

## Data

1. Which public air quality dataset has the cleanest units?
2. How should missing pollutant values be handled?
3. Should PM2.5 and PM10 be estimated separately or combined?
4. How should concentration units be converted into ppm or density units required by the forward model?

## Estimation

1. Does Ridge remain competitive once HITRAN lines are used?
2. Does PLS outperform Ridge for correlated spectra?
3. Can a physics informed template estimator beat generic ML?
4. What is the detection floor for each gas?
5. Which error metric should define the minimum error result?

