# What pet gets adopted the fastest and why

Although everyone has their own vision of the perfect pet when a lot of people make a decision about which pets they adopt we can study that data and try to predict why.  In this data mining lab, I am exploring a dataset from PetFinder, which is a malaysian pet adoption service, to find out the characteristics of animals who get adopted the fastest and the slowest.

## TL;DR

- Younger pets are predicted to be adopted faster, while adoption speed becomes progressively slower as pets get older.
- Single-pet listings are predicted to be adopted faster than listings for multiple pets or litters.  Higher adoption fees are also associated with slower adoption.
- The very common Mixed Breed and Domestic Short Hair categories are associated with slower predicted adoption, while small-sample breed rankings are not reliable enough to trust.
- One surprising pattern is that sterilized pets are predicted to adopt more slowly.  This is likely related to other factors, such as age or rescue history, rather than sterilization itself causing a slower adoption.

These are predictive associations in this dataset, not causal conclusions.

### A quick look at the data -  Data Understating

The dataset has 14,993 pet listings that have information like the pet's age, type, breed, gender, size, health status, fee, number of photos, and a written description from the person who posted the pet.  The dataset contains Cats and Dogs (slightly dominated by dogs). In this experiment we are predicting the "AdoptionSpeed" which is defined by a scale from 0 - 4.

| AdoptionSpeed | What it means |
| --- | --- |
| 0 | Adopted on the same day it was listed |
| 1 | Adopted in 1-7 days |
| 2 | Adopted in 8-30 days |
| 3 | Adopted in 31-90 days |
| 4 | Not adopted within 100 days |

One thing I noticed right away is that the classes are not split evenly. Only 410 pets, about 2.7% of the dataset, were adopted on the same day, while almost 28% are in the slowest category. This tells us that we need to look at class-wise accuracy instead of overall accuracy. The model could learn to always guess the slowest adoption and get a good score. This would not be helpful especially if we want to identify animals that might need help. 

The data is mostly complete, which is helpful.  There are 1,265 pet names missing, which is 8.44% of the listings, and only 13 descriptions are missing, which is 0.09%.  The rest of the main columns do not have missing values.  There are also photos, image information, and sentiment files for most pets, although not every listing has them.  Photo and image data covers 14,652 listings (97.73%), while sentiment data covers 14,442 listings (96.32%).  I will keep those missing cases instead of throwing them out because pets with no photos may actually be different from pets with photos.  Before making any conclusions, I also need to remember that this dataset can show patterns, but it cannot prove that one characteristic directly causes a pet to be adopted faster or slower.

### Initial patterns in the data

![Adoption speed by age band, pet type, and state](/Users/oleg/Documents/Coding/SJSU/Data%20Mining/pipeline/figures/relationship_eda.png)

This chart shows two early patterns from the dataset.  On the left, lower AdoptionSpeed means faster adoption.  Cats in the 0-2 month age group have the lowest average AdoptionSpeed, while adoption speed generally becomes slower after the first two months for both cats and dogs.  This is a descriptive pattern, so it does not prove that age or pet type is the reason an animal was adopted at a certain speed.

The chart on the right shows the average AdoptionSpeed by state.  The size of each point represents the number of listings from that state.  Selangor and Kuala Lumpur contain most of the data, while some states have very few listings.  Because of this, the results from small states like Labuan, Sarawak, and Kelantan are less reliable and should not be treated as strong conclusions.

### Data Processing

Before training any models, I created one row-level feature table where each row still represents one pet listing.  I started with the original 14,993 records and joined the sentiment and image-metadata files using `PetID` as the key.  The final preparation table has 14,993 rows and 62 columns, so no listings were removed during the merge.  `PetID` was then excluded from the model because it is only an identifier and does not describe the pet.  I also excluded `RescuerID` from the initial models because it has 5,595 unique values.  Including it could allow the model to memorize particular rescuers instead of learning general patterns about pet adoption.

Missing data was handled carefully instead of simply dropping the rows.  The name and description fields have availability indicators and text-length features, while the sentiment and image features have their own availability indicators.  For example, a listing without a photo keeps `image_pixels_available = 0` and has missing image-derived values.  This is important because no photo is potentially meaningful information, rather than just a value that should be replaced with zero.  The numeric missing values were imputed using statistics calculated from the training split only, and the missingness indicators were kept as separate model features.

The structured variables were separated into categorical and numeric feature groups.  Pet type, breed, color, gender, maturity size, fur length, health status, and state were treated as categorical variables.  Age, quantity, fee, photo count, and video count were treated as numeric variables.  The duplicate image-count fields created during the join were removed because they exactly match `PhotoAmt`, so leaving all of them would give the same information extra weight in the model.

I also engineered features from the additional data sources.  The text data produced name and description length features, as well as TF-IDF word and two-word phrase features from the listing descriptions.  The sentiment files provided sentiment score, magnitude, sentence count, token count, and entity count.  Image metadata was aggregated across all of a listing's photos to measure features such as average label confidence and the number of unique labels.  Direct image processing added photo dimensions, aspect ratio, brightness, contrast, colorfulness, and edge-variance features.  These are descriptive features, not a claim that a brighter or more colorful photo directly causes faster adoption.

To avoid data leakage, transformations that learn from the data were fit only on the training portion of each split.  This includes imputing missing values, scaling numeric variables, encoding categories, and building the TF-IDF vocabulary.  The validation portion was transformed using only what was learned from the training portion.  This gives a more realistic estimate of how the model will perform when it receives a new pet listing that it has never seen before.

### Modeling

Because `AdoptionSpeed` is an ordered target, I used Quadratic Weighted Kappa (QWK) as the main model-selection metric.  QWK gives more credit when a prediction is close to the correct adoption-speed category and penalizes predictions that are farther away.  For example, predicting 3 when the true value is 4 is less severe than predicting 0 when the true value is 4.  Accuracy was also recorded, but it was not the main metric because it treats every incorrect category as equally wrong.

I evaluated the models with 5-fold cross-validation rather than using one train/test split.  I used two validation strategies.  Stratified cross-validation keeps the class distribution similar in each fold and measures performance when the model sees similar types of listings during training.  I also used rescuer-grouped cross-validation, where listings from the same `RescuerID` stay in the same fold.  This is a more difficult and realistic test because the model must predict adoption speed for pets posted by rescuers it has not seen during training.

The first model was a majority-class baseline, which always predicted the most common adoption-speed category.  I then tested multinomial logistic regression as a linear baseline, followed by CatBoost and LightGBM boosted-tree models.  The comparison below shows the main QWK results.  The rescuer-grouped score was used as the primary score when choosing the final model because it is the more conservative estimate of generalization.

![Model comparison: stratified and rescuer-grouped QWK](/Users/oleg/Documents/Coding/SJSU/Data%20Mining/pipeline/figures/model_comparison_table.png)

The baseline confirms that the model needs to use the listing features to make useful predictions.  The boosted-tree models performed better than logistic regression because they can learn non-linear relationships and interactions between features.  Even though LightGBM had the highest stratified score, its grouped score dropped more than CatBoost's.  This suggests that LightGBM was less reliable when predicting for previously unseen rescuers, so I did not select it as the final model.

Feature-family testing also showed that using more than the original spreadsheet columns helped.  The core tabular features reached a stratified QWK of 0.276 with logistic regression.  Adding image metadata and direct image features increased it to 0.303, while adding TF-IDF text features from the descriptions increased it again to 0.323.  The final CatBoost model used the complete feature set: structured listing data, text features, sentiment, image metadata, direct image measurements, and frozen ResNet18 image embeddings.  The text was reduced with Truncated SVD and the image embeddings were reduced with PCA, with both transformations fit inside the training fold only.

The final model was a CatBoost regressor with depth 6, a learning rate of 0.05, and L2 regularization of 3.  Instead of treating the five adoption-speed categories as unrelated classes, it predicted a continuous adoption-speed value using RMSE loss.  The continuous prediction was then converted back into categories using four optimized thresholds.  The thresholds were fit only using predictions from the training process, never the outer validation fold.  This ordinal approach improved the rescuer-grouped QWK from 0.353 for the multiclass CatBoost model to 0.379, making it the final model selected for evaluation.

### Evaluation

The final model was evaluated using out-of-fold predictions from rescuer-grouped 5-fold cross-validation.  This means every prediction was made for a listing that was not used to train that particular fold, and no rescuer appeared in both the training and validation data for the same fold.  The final model achieved a QWK of 0.379, a mean absolute error (MAE) of 0.865 adoption-speed categories, an accuracy of 36.7%, and a macro F1 score of 0.265.  The QWK result is the most important one because the target is ordinal.  A QWK of 0.379 represents fair to moderate agreement, so the model can support decisions but is not accurate enough to make adoption decisions automatically.

![Row-normalized confusion matrix for the final ordinal model](/Users/oleg/Documents/Coding/SJSU/Data%20Mining/pipeline/figures/ordinal_model_confusion_matrix.png)

The confusion matrix shows the true adoption-speed category on the left and the predicted category on the bottom.  Each row is normalized, so the values show the percentage of each true class that was predicted in each category.  The model performed best on the slowest category, class 4, where it correctly identified 50.0% of listings.  It also identified 60.7% of class-2 listings correctly.  However, it only identified 18.7% of class-3 listings correctly, and it did not correctly predict any class-0 same-day adoptions.

![Final model recall by adoption-speed category](/Users/oleg/Documents/Coding/SJSU/Data%20Mining/pipeline/figures/class_recall_table.png)

The most important limitation is the class-0 result.  Same-day adoption is the rarest class, with only 410 listings, and the model predicted none of them correctly.  Because of this, the model should not be used to identify pets that are likely to be adopted on the same day.  A future improvement would be to test class weighting, oversampling, or a separate binary model for same-day adoption.

I also checked whether performance changed for meaningful groups of pets.  The grouped QWK was 0.391 for dogs and 0.343 for cats.  It was lowest for pets aged 0-2 months (0.263) and highest for pets older than 60 months (0.411), which means the model was less reliable for younger pets.  Listings with at least one photo had a QWK of 0.378, but listings with no photo had a QWK of only 0.085.  Therefore, predictions for photo-less listings should be treated with extra caution.  These differences show where the model is more and less reliable; they do not prove that being a dog, cat, young, or without a photo causes a certain adoption outcome.

Finally, these results are cross-validation estimates from the labeled training data, not results from an independent held-out test set.  The evaluation is useful for comparing models and identifying limitations, but the model should be tested on new future listings before it is used in a real adoption-support setting.

### Overall Findings

The final model found several clear and consistent associations with predicted adoption speed.  The chart below ranks features by their average SHAP value, which measures how much a feature typically changes the model's prediction.  It shows the size of each feature's effect, not whether that effect makes adoption faster or slower.

![Top features by average SHAP importance](/Users/oleg/Documents/Coding/SJSU/Data%20Mining/pipeline/figures/shap_chart_1_overall_importance.png)

Age was the strongest numeric driver in the model.  The correlation between age and its SHAP contribution was 0.57, and the relationship was monotonic across age quartiles: as pets became older, the model predicted progressively slower adoption.  This agrees with the early exploratory analysis, where adoption speed was generally slower after the first two months of age.

Quantity had the strongest directional relationship of any numeric feature, with a correlation of 0.89 between quantity and its SHAP contribution.  Listings containing multiple pets or litters were predicted to be adopted more slowly than single-pet listings.  Fee also had a strong positive relationship with slower predicted adoption (correlation = 0.70): higher adoption fees were associated with slower adoption predictions.

Breed was one of the most important categorical features.  The two most common breed categories, Mixed Breed (5,923 listings) and Domestic Short Hair (3,634 listings), both pushed predictions toward slower adoption.  One possible explanation is that these common categories compete with many similar listings, but the data cannot prove that this is the reason.  The individual breeds with the fastest predicted adoption, such as Pug, Yorkshire Terrier, and Papillon, had only 2-21 listings each.  Those small sample sizes are too limited to support reliable breed-specific conclusions.

One counterintuitive result was that `Sterilized = Yes` was associated with slower predicted adoption, while `Sterilized = No` was associated with faster predictions.  This should not be interpreted as sterilization causing slower adoption or as advice against sterilizing pets.  A more likely explanation is confounding: sterilized pets may differ in age, rescue history, health, or other factors that are related to adoption speed but are not fully measured in this dataset.  This finding needs more controlled analysis before it could support any recommendation.

Gender had a smaller effect, with male pets predicted modestly faster than female or mixed groups.  State-level effects should also be interpreted carefully.  Perak, Pulau Pinang, and Negeri Sembilan have the largest samples among the smaller states (roughly 250-850 listings), but state comparisons can still reflect differences in rescuers, local demand, and types of animals listed rather than location itself.

The image and text components also carried useful predictive signal.  Two frozen image-embedding components, `img_emb_pca_2` and `img_emb_pca_4`, ranked among the top five features by average importance.  However, these components are compressed combinations of hundreds of image features, so they cannot be interpreted as a specific visual concept without inspecting the listings at their highest and lowest values.  The same caution applies to the text components: they help prediction, but their importance may partially reflect different rescuer writing styles rather than only the content quality of a description.

Overall, the most trustworthy conclusion is that the model can identify broad risk patterns, especially for older pets, multi-pet listings, and higher-fee listings.  It is best used as a decision-support tool to help prioritize attention, not as an automated system that decides which pets will be adopted quickly.  The strongest next step would be to improve prediction of same-day adoption and to validate the model on new future listings.
