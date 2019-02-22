# im_data
#### Intelligent Marketing Data
###### Real Time Consumer Data Appending API

Append Data by:

- ip address
- mobile number
- street address
- city
- zip code
- designated market area (dma)
- metro code
- consumer name


API Routes:

```
'/api/v1.0/auth/login'
'/api/v1.0/ipaddr/<string:ip_addr>'
'/api/v1.0/sms/<string:sms_number>'
'/api/v1.0/addr/<string:addr>'
'/api/v1.0/lat/<string:lat>/lng/<string:lng>'
'/api/v1.0/name/first/<string:f_name>/last/<string:l_name>'
'/api/v1.0/zipcode/<string:zip_code>'
'/api/v1.0/city/<string:city_name>/limit/<int:limit>'
```