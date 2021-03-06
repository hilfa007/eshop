from django.http import JsonResponse,HttpResponse
from django.db.models import Max,Min,Count,Avg
from django.shortcuts import render,redirect
from .models import *
from django.template.loader import render_to_string
from .forms import ReviewAdd, SignupForm
from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
#paypal
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm


# home page
def home(request):
    banners=Banner.objects.all().order_by('-id')
    data=Product.objects.filter(is_featured=True).order_by('-id')
    return render(request,'index.html',{'data':data,'banners':banners})

# category
def category_list(request):
    data = Categories.objects.all().order_by('-id')
    return render(request,'category_list.html',{'data':data})

# brand
def brand_list(request):
    data=Brand.objects.all().order_by('-id')
    return render(request,'brand_list.html',{'data':data})

# product
def product_list(request):
    total_data=Product.objects.count()
    data=Product.objects.all().order_by('-id')[:3]
    min_price=ProductAttribute.objects.aggregate(Min('price'))
    max_price=ProductAttribute.objects.aggregate(Max('price'))
    return render(request,'product_list.html',
    {
        'data':data,
		'total_data':total_data,
		'min_price':min_price,
		'max_price':max_price,
        
        })

# product list according to category
def category_product_list(request,cat_id):
    category=Categories.objects.get(id=cat_id)
    data=Product.objects.filter(category=category).order_by('-id')
    return render(request,'category_product_list.html',{'data':data,})

# product list according to brand
def brand_product_list(request,brand_id):
    brand=Brand.objects.get(id=brand_id)
    data=Product.objects.filter(brand=brand).order_by('-id')
    return render(request,'category_product_list.html',{'data':data,})

# product detail
def product_detail(request,slug,id):
    product=Product.objects.get(id=id)

    # related products
    related_products=Product.objects.filter(category=product.category).exclude(id=id)[:4]


    colors=ProductAttribute.objects.filter(product=product).values('color__id','color__title','color__color_code').distinct()
    sizes=ProductAttribute.objects.filter(product=product).values('size__id','size__title','price','color__id').distinct()

    # review
    reviewForm=ReviewAdd()

	# Check
    canAdd=True
    reviewCheck=ProductReview.objects.filter(user=request.user,product=product).count()
    if request.user.is_authenticated:
        if reviewCheck > 0:
            canAdd=False
    #end
    
    #fetch reviews
    reviews=ProductReview.objects.filter(product=product)
    #end

	# Fetch avg rating for reviews
    avg_reviews=ProductReview.objects.filter(product=product).aggregate(avg_rating=Avg('review_rating'))
	# End

    return render(request, 'product_detail.html',{'data':product,'related':related_products,'colors':colors,'sizes':sizes,'reviewForm':reviewForm,'canAdd':canAdd,'reviews':reviews,'avg_reviews':avg_reviews})

# search
def search(request):
    q=request.GET['q']
    data=Product.objects.filter(title__icontains=q,).order_by('-id')
    return render(request,'search.html',{'data':data,})

# filter data
def filter_data(request):
    colors=request.GET.getlist('color[]')
    categories=request.GET.getlist('category[]')
    brands=request.GET.getlist('brand[]')
    sizes=request.GET.getlist('size[]')
    minPrice=request.GET['minPrice']
    maxPrice=request.GET['maxPrice']
    allProducts=Product.objects.all().order_by('-id').distinct()
    allProducts=allProducts.filter(productattribute__price__gte=minPrice)
    allProducts=allProducts.filter(productattribute__price__lte=maxPrice)
    if len(colors)>0:
        #searching color in productattribute section
        allProducts=allProducts.filter(productattribute__color__id__in=colors).distinct()
    if len(categories)>0:
        allProducts=allProducts.filter(category__id__in=categories).distinct()
    if len(brands)>0:
        allProducts=allProducts.filter(brand__id__in=brands).distinct()
    if len(sizes)>0:
        allProducts=allProducts.filter(productattribute__size__id__in=sizes).distinct()
    t=render_to_string('ajax/product-list.html',{'data':allProducts})
    return JsonResponse({'data':t})
    
# load more data
def load_more_data(request):
    offset=int(request.GET['offset'])
    limit=int(request.GET['limit'])
    total_data=Product.objects.count()
    data=Product.objects.all().order_by('-id')[offset:offset+limit]
    t=render_to_string('ajax/product-list.html',{'data':data})
    return JsonResponse({'data':t})

# Add to cart
def add_to_cart(request):
    
    cart_p={}
    cart_p[str(request.GET['id'])]={
        'image':request.GET['image'],
    	'title':request.GET['title'],
    	'qty':request.GET['qty'],
    	'price':request.GET['price']
    }
    if 'cartdata' in request.session:
        if str(request.GET['id']) in request .session['cartdata']:
            cart_data=request.session['cartdata']
            cart_data[str(request.GET['id'])]['qty']=int(cart_p[str(request.GET['id'])]['qty'])
            cart_data.update(cart_data)
            request.session['cartdata']=cart_data
        else:
            cart_data=request.session['cartdata']
            cart_data.update(cart_p)
            request.session['cartdata']=cart_data

    else:
        request.session['cartdata']=cart_p
    return JsonResponse({'data' : request.session['cartdata'],'totalitems':len(request.session['cartdata'])})

# cart list page
def cart_list(request):
    total_amt=0
    if 'cartdata' in request.session:
        for p_id,item in request.session['cartdata'].items():
            total_amt+=int(item['qty'])*float(item['price'])
        return render(request,'cart.html',{'cart_data' : request.session['cartdata'],'totalitems':len(request.session['cartdata']),'total_amt':total_amt})
    return render(request,'cart.html')

# update cart item
def update_cart_item(request):
    p_id=str(request.GET['id'])
    p_qty=request.GET['qty']
    if 'cartdata' in request.session:
        if p_id in request.session['cartdata']:
            cart_data=request.session['cartdata']
            cart_data[str(request.GET['id'])]['qty']=p_qty
            request.session['cartdata']=cart_data
    total_amt=0
    for p_id,item in request.session['cartdata'].items():
        total_amt+=int(item['qty'])*float(item['price'])
    t=render_to_string('ajax/cart-list.html',{'cart_data' : request.session['cartdata'],'totalitems':len(request.session['cartdata']),'total_amt':total_amt ,})
    return JsonResponse({'data':t,'totalitems':len(request.session['cartdata'])})
    
# delete cart item
def delete_cart_item(request):
    p_id=str(request.GET['id'])
    if 'cartdata' in request.session:
        if p_id in request.session['cartdata']:
            cart_data=request.session['cartdata']
            del request.session['cartdata'][p_id]
            request.session['cartdata']=cart_data
    total_amt=0
    for p_id,item in request.session['cartdata'].items():
        total_amt+=int(item['qty'])*float(item['price'])
    t=render_to_string('ajax/cart-list.html',{'cart_data' : request.session['cartdata'],'totalitems':len(request.session['cartdata']),'total_amt':total_amt ,})
    return JsonResponse({'data':t,'totalitems':len(request.session['cartdata'])})

# Signup
def signup(request):
    if request.method=='POST':
        form=SignupForm(request.POST)
        if form.is_valid():
            form.save()
            username=form.cleaned_data.get('username')
            pwd=form.cleaned_data.get('password1')
            user=authenticate(username=username,password=pwd)
            login(request, user)
            return redirect('home')
    form=SignupForm
    return render(request, 'registration/signup.html',{'form':form})

# Checkout
@login_required
def checkout(request):
	total_amt=0
	totalAmt=0
	if 'cartdata' in request.session:
		for p_id,item in request.session['cartdata'].items():
			totalAmt+=int(item['qty'])*float(item['price'])
		# Order
		order=CartOrder.objects.create(
				user=request.user,
				total_amt=totalAmt
			)
		# End
		for p_id,item in request.session['cartdata'].items():
			total_amt+=int(item['qty'])*float(item['price'])
			# OrderItems
			items=CartOrderItems.objects.create(
				order=order,
				invoice_no='INV-'+str(order.id),
				item=item['title'],
				image=item['image'],
				qty=item['qty'],
				price=item['price'],
				total=float(item['qty'])*float(item['price'])
				)
			# End
		# Process Payment
		host = request.get_host()
		paypal_dict = {
		    'business': settings.PAYPAL_RECEIVER_EMAIL,
		    'amount': total_amt,
		    'item_name': 'OrderNo-'+str(order.id),
		    'invoice': 'INV-'+str(order.id),
		    'currency_code': 'USD',
		    'notify_url': 'http://{}{}'.format(host,reverse('paypal-ipn')),
		    'return_url': 'http://{}{}'.format(host,reverse('payment_done')),
		    'cancel_return': 'http://{}{}'.format(host,reverse('payment_cancelled')),
		}
		form = PayPalPaymentsForm(initial=paypal_dict)
		return render(request, 'checkout.html',{'cart_data':request.session['cartdata'],'totalitems':len(request.session['cartdata']),'total_amt':total_amt,'form':form})

@csrf_exempt
def payment_done(request):
	returnData=request.POST
	return render(request, 'payment-success.html',{'data':returnData})


@csrf_exempt
def payment_canceled(request):
	return render(request, 'payment-fail.html')

# Save Review
def save_review(request,pid):
	product=Product.objects.get(pk=pid)
	user=request.user
	review=ProductReview.objects.create(
		user=user,
		product=product,
		review_text=request.POST['review_text'],
		review_rating=request.POST['review_rating'],
		)
	data={
		'user':user.username,
		'review_text':request.POST['review_text'],
		'review_rating':request.POST['review_rating']
	}

	# Fetch avg rating for reviews
	avg_reviews=ProductReview.objects.filter(product=product).aggregate(avg_rating=Avg('review_rating'))
	# End

	return JsonResponse({'bool':True,'data':data,'avg_reviews':avg_reviews})