# BOSGIR
Text adventure game powered by the magic of LLMs.

Bald Old Short Guy In Red (or BOSGIR) is powered by the Bedrock service on AWS, so it requires and account there in order to play. It is a fully text-drive app, running on the client in a command-line window, with a UI powered by curses.

## Installation

### Prerequisites
* Python w/Pip
* AWS account
* AWS CLI

### AWS Setup
BOSGIR relies on AWS to provide the LLM powering the game. Specifically, it uses the Bedrock service to invoke the Claude LLMs via an API. There is no requirement to deploy infrastructure via CloudFormation or anything, it just needs the Bedrock API which provides everything else. But there is some configuration required in the AWS console in order to be able to access the right foundation models.

1. Decide which AWS region you will be using. Basically, if you're on the east coast, it will be `us-east-1`, on the west coast it will be `us-west-2`. This decision shouldn't have any impact on your bill from AWS in regards to the Bedrock service.
1. Browse to the AWS IAM console: https://???.console.aws.amazon.com/iam/home?region=???#/users (replace both ???'s with the region string from the previous step)
**If this is the first time you've ever accessed the console, you will be logging in with your root account. If not, use whichever login has enough permissions to create a new user**
1. Click "Create user" ![Create user](imgs/install01.png)
1. Enter "bosgir_api" for the user name, leave the checkbox unchecked, click Next ![User details](imgs/install02.png)
1. On the Permissions page, click "Attach policies directly," then the "Create policy" button ![Permissions options](imgs/install03.png)
1. A new tab should open; click the Service drop-down and choose the Bedrock service ![Select service](imgs/install04.png)
1. Expand the Read list ![Actions allowed](imgs/install05.png)
1. Check "InvokeModel" and "InvokeModelWithResponseStream" ![InvokeModel](imgs/install06.png)
1. Scroll down to Resources and select the "All" radio button and click Next ![Resources](imgs/install07.png)
1. Name the policy "bedrock" then click Create policy ![Create policy](imgs/install08.png)
1. Close the Policies tab and go back to the Set Permissions tab for the new user. Click the refresh button next to the "Create policy" button, enter "bedrock" in the search box, check the policy you just created, then click Next ![Attach permissions](imgs/install09.png)
1. Click "Create user" ![Create user](imgs/install0.png)
1. Click on the "bosgir_api" user you just created ![User select](imgs/install11.png)
1. Click on the "Security Credentials tab, then click the "Create access key" button ![Security Credentials](imgs/install12.png)
1. Select "Local code," then check the check box at the bottom, then click Next ![Access key best practices](imgs/install13.png)
1. Click "Create access key" ![Create access key](imgs/install14.png)
1. Click the copy icons next to each key (Access key and Secrete access key) and copy them into Notepad or another text editor; you will need them later. Click Done (Click Continue if you get a warning dialog about not viewing or downloading your key). ![Copy keys](imgs/install15.png)
1. You should see your access key listed on the user's Access keys section with an active status ![Access key status](imgs/install16.png)

### AWS CLI Setup
1. Install the AWS CLI by following [these instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

1. Open a command line

1. Execute the following: `aws 
