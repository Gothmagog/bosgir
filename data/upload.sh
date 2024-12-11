for file in lovecraft/processed/*.txt; do
	echo "Uploading $file..."
	aws --profile me s3 cp $file s3://sagemaker-us-west-2-705853895572/data/lovecraft/
done
